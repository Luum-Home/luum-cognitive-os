#!/usr/bin/env bash
# SCOPE: os-only
# PreToolUse:Agent hook — Adaptive dispatch quota advisor (ADR-056 L1).
#
# Computes a quota-pressure score from .cognitive-os/metrics/llm-dispatch.jsonl
# and cost-events.jsonl (last 30min window). When pressure crosses threshold,
# emits an advisory via hookSpecificOutput.additionalContext suggesting the
# user/orchestrator route through `scripts/orchestrator.py --providers
# qwen,claude` instead of the native Agent() tool.
#
# L1 is advisory-only: never blocks, always exits 0. Thresholds:
#   pressure < 0.5  -> silent (normal operation)
#   pressure 0.5-0.8 -> warning ("usage at N%, consider Qwen fallback")
#   pressure > 0.8   -> strong advisory (mentions COS_AUTO_REDIRECT_AGENT=1 for L2)
#
# Kill-switch: COS_DISABLE_AGENT_ADVISOR=1 silences this hook entirely.
# Graceful degradation: missing JSONL files -> pressure = 0.0 -> silent exit.
#
# Must complete in <500ms. Reference: hooks/blast-radius.sh for the
# additionalContext pattern; lib/quota_pressure.py for the math.

set -uo pipefail

# Respect killswitch flag per ADR-028 (non-critical hook).
if [ -f "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh" ]; then
  source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
fi

# Explicit kill-switch.
if [ "${COS_DISABLE_AGENT_ADVISOR:-}" = "1" ]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"

# Read stdin — Claude Code hook contract.
INPUT=""
if [ ! -t 0 ]; then
  INPUT=$(cat 2>/dev/null || true)
fi

# Only process Agent tool invocations.
if command -v jq >/dev/null 2>&1 && [ -n "$INPUT" ]; then
  TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
  if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Agent" ]; then
    exit 0
  fi
fi

# Locate Python. Prefer project UV env, fall back to system python3.
PY_BIN="python3"
if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
  PY_BIN="$PROJECT_DIR/.venv/bin/python"
fi

# Compute pressure via lib/quota_pressure.py. Pass metrics dir via arg to
# keep the call hermetic (no env leakage between agent runs).
PRESSURE=$("$PY_BIN" - "$METRICS_DIR" <<'PYEOF' 2>/dev/null || echo "0.0"
import sys
from pathlib import Path

# Ensure repo root is on sys.path so `lib.quota_pressure` resolves.
metrics = Path(sys.argv[1])
# Walk up from metrics dir to find repo root (where lib/ lives).
root = metrics.parent.parent if metrics.name == "metrics" else metrics
for _ in range(4):
    if (root / "lib" / "quota_pressure.py").exists():
        sys.path.insert(0, str(root))
        break
    root = root.parent

try:
    from lib.quota_pressure import compute_quota_pressure
    p = compute_quota_pressure(metrics)
    print(f"{p:.4f}")
except Exception:
    print("0.0")
PYEOF
)

# Normalize to a comparable integer percentage (avoid bash float pain).
PCT=$(printf '%s' "$PRESSURE" | awk '{ printf "%d", ($1 * 100) + 0.5 }')
if ! [[ "$PCT" =~ ^[0-9]+$ ]]; then
  PCT=0
fi

# Threshold routing.
if [ "$PCT" -lt 50 ]; then
  # LOW — silent, most common path.
  exit 0
fi

emit_additional_context() {
  local context="$1"
  if command -v jq >/dev/null 2>&1; then
    jq -c -n --arg ctx "$context" \
      '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "allow", additionalContext: $ctx}}'
  else
    # jq absent — degrade to stderr advisory so the signal isn't lost.
    printf '%s\n' "$context" >&2
  fi
}

if [ "$PCT" -ge 80 ]; then
  MSG="ADR-056 L1 QUOTA ADVISORY (strong): Claude Max quota pressure ~${PCT}%. Native Agent() may fail mid-run. Strongly consider 'scripts/orchestrator.py --providers qwen,claude' for this task. To enable auto-redirect (L2), set COS_AUTO_REDIRECT_AGENT=1 (not yet shipped)."
else
  MSG="ADR-056 L1 QUOTA ADVISORY: Claude Max quota pressure ~${PCT}%. Consider routing via 'scripts/orchestrator.py --providers qwen,claude' to preserve primary-chat quota."
fi

emit_additional_context "$MSG"

exit 0
