#!/usr/bin/env bash
# SCOPE: os-only
# agent-quota-redirect.sh — PreToolUse:Agent hook (ADR-056 Level 2)
#
# Opt-in hook that BLOCKS native Agent() launches when Claude Max quota
# pressure is high, redirecting the orchestrator to dispatch via
# scripts/orchestrator.py (qwen primary, claude fallback) instead.
#
# The hook emits a 2-line structured AGENT_REDIRECT block on stderr and
# exits 2 (blocking exit code). The parent orchestrator parses the block
# via lib.agent_redirect_protocol.parse_redirect_message() and re-issues
# the call through the orchestrator CLI.
#
# Gating (ALL must be true to block):
#   1. COS_AUTO_REDIRECT_AGENT=1 (explicit opt-in; default OFF)
#   2. COS_DISABLE_AGENT_REDIRECT unset/≠1 (hard kill-switch)
#   3. Not running under CI=1 or PYTEST_CURRENT_TEST (tests never blocked)
#   4. quota_pressure > 0.7  OR  rate-limit event in last 5 min
#
# Exit codes:
#   0 — no-op (opt-in off, bypass active, or pressure below threshold)
#   2 — BLOCK (Claude Code treats exit 2 as "deny tool call"; stderr is
#       shown to the orchestrator which parses AGENT_REDIRECT)
#
# Logs every decision to .cognitive-os/metrics/agent-redirect.jsonl.
#
# Reference: docs/adrs/ADR-056-adaptive-agent-dispatch.md (Level 2).

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
METRICS_FILE="$METRICS_DIR/agent-redirect.jsonl"
RATE_LIMIT_FILE="$METRICS_DIR/rate-limit-events.jsonl"
PRESSURE_THRESHOLD="${COS_QUOTA_PRESSURE_THRESHOLD:-0.7}"
RATE_LIMIT_WINDOW_SEC="${COS_RATE_LIMIT_WINDOW_SEC:-300}"

mkdir -p "$METRICS_DIR" 2>/dev/null || true

now_iso() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

log_event() {
  # $1 = decision (noop|block|bypass), $2 = reason, $3 = pressure (or "")
  local decision="$1" reason="$2" pressure="${3:-}"
  printf '{"ts":"%s","decision":"%s","reason":"%s","pressure":"%s"}\n' \
    "$(now_iso)" "$decision" "$reason" "$pressure" \
    >> "$METRICS_FILE" 2>/dev/null || true
}

# ── Kill-switches (hard bypass) ───────────────────────────────────────
if [ "${COS_DISABLE_AGENT_REDIRECT:-}" = "1" ]; then
  log_event bypass "disabled_hard_killswitch" ""
  exit 0
fi

# Tests must never be blocked by this hook — they seed fixtures that
# would otherwise trigger it.
if [ "${CI:-}" = "1" ] || [ -n "${PYTEST_CURRENT_TEST:-}" ]; then
  log_event bypass "test_environment" ""
  exit 0
fi

# ── Opt-in check (default OFF) ────────────────────────────────────────
if [ "${COS_AUTO_REDIRECT_AGENT:-}" != "1" ]; then
  # L1 advisory hook (agent-quota-advisor.sh) may still emit warnings;
  # this L2 block hook is entirely inert until explicitly enabled.
  exit 0
fi

# ── Read hook stdin ───────────────────────────────────────────────────
INPUT=""
if [ ! -t 0 ]; then
  INPUT="$(cat || true)"
fi

# Extract the original prompt. Claude Code PreToolUse:Agent payload is
# JSON with tool_input.prompt. We parse with Python to avoid a jq
# dependency and to handle multi-line prompts safely.
PROMPT=""
if [ -n "$INPUT" ]; then
  PROMPT=$(printf '%s' "$INPUT" | uv run python3 -c '
import json, sys
try:
    data = json.loads(sys.stdin.read())
    prompt = (data.get("tool_input") or {}).get("prompt") or ""
    sys.stdout.write(prompt)
except Exception:
    pass
' 2>/dev/null || true)
fi
[ -z "$PROMPT" ] && PROMPT="(original prompt unavailable)"

# ── Compute quota pressure + rate-limit signal ────────────────────────
# Uses lib/quota_pressure.py when available (Agent A's artifact). Falls
# back to a local stub that reads rate-limit-events.jsonl directly so
# this hook ships independently.
PRESSURE_AND_RL=$(uv run python3 -c "
import json, os, sys, time
from pathlib import Path

project_dir = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
sys.path.insert(0, project_dir)

pressure = 0.0
rate_limit_recent = False
window = int(os.environ.get('COS_RATE_LIMIT_WINDOW_SEC', '300'))

# Preferred path: Agent A's lib/quota_pressure.py
try:
    from lib.quota_pressure import compute_quota_pressure  # type: ignore
    pressure = float(compute_quota_pressure())
except Exception:
    # Stub fallback: pressure based on recent rate-limit density.
    # One event in window -> 0.75, two -> 0.85, three+ -> 0.95.
    pressure = 0.0

# Rate-limit recency is computed directly from the JSONL regardless of
# whether quota_pressure.py is present — it's the harder signal.
rl_file = Path(project_dir) / '.cognitive-os' / 'metrics' / 'rate-limit-events.jsonl'
if rl_file.exists():
    cutoff = time.time() - window
    count = 0
    try:
        with rl_file.open() as fh:
            # Tail the last 50 lines only (cheap).
            lines = fh.readlines()[-50:]
        for line in lines:
            try:
                rec = json.loads(line)
                ts = rec.get('ts', '')
                # Parse ISO-8601 Z timestamps
                import datetime as _dt
                dt = _dt.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=_dt.timezone.utc)
                if dt.timestamp() >= cutoff:
                    count += 1
            except Exception:
                continue
    except Exception:
        pass
    if count >= 1:
        rate_limit_recent = True
        # Stub pressure escalation when quota_pressure.py missing.
        if pressure == 0.0:
            pressure = min(0.75 + 0.05 * (count - 1), 0.95)

print(f'{pressure:.4f}|{1 if rate_limit_recent else 0}')
" 2>/dev/null || echo "0.0000|0")

CURRENT_PRESSURE="${PRESSURE_AND_RL%%|*}"
RATE_LIMIT_RECENT="${PRESSURE_AND_RL##*|}"

# ── Decide: block or pass ─────────────────────────────────────────────
# Compare pressure as float via awk (bash doesn't do float comparison).
over_threshold=$(awk -v p="$CURRENT_PRESSURE" -v t="$PRESSURE_THRESHOLD" \
  'BEGIN { print (p+0 > t+0) ? 1 : 0 }')

REASON=""
if [ "$over_threshold" = "1" ]; then
  REASON="quota_pressure"
elif [ "$RATE_LIMIT_RECENT" = "1" ]; then
  REASON="rate_limit"
fi

if [ -z "$REASON" ]; then
  log_event noop "below_threshold" "$CURRENT_PRESSURE"
  exit 0
fi

# ── Block: emit AGENT_REDIRECT block on stderr + exit 2 ───────────────
# Use the Python helper for stable formatting + safe shlex quoting. If
# the import fails for any reason, fall back to a hand-built block.
BLOCK_MSG=$(PROMPT_ENV="$PROMPT" REASON_ENV="$REASON" PRESSURE_ENV="$CURRENT_PRESSURE" \
  uv run python3 -c "
import os, sys
sys.path.insert(0, os.environ['CLAUDE_PROJECT_DIR'] if os.environ.get('CLAUDE_PROJECT_DIR') else os.getcwd())
try:
    from lib.agent_redirect_protocol import build_redirect_message
    sys.stdout.write(build_redirect_message(
        reason=os.environ['REASON_ENV'],
        pressure=float(os.environ['PRESSURE_ENV']),
        prompt=os.environ['PROMPT_ENV'],
    ))
except Exception as exc:
    sys.stderr.write(f'redirect_build_failed: {exc}\n')
    sys.exit(1)
" 2>/dev/null) || BLOCK_MSG=""

if [ -n "$BLOCK_MSG" ]; then
  printf '%s' "$BLOCK_MSG" >&2
else
  # Minimal hand-built fallback (no shlex; best-effort).
  printf 'AGENT_REDIRECT: reason=%s pressure=%.2f\n' \
    "$REASON" "$CURRENT_PRESSURE" >&2
  printf "SUGGESTED_COMMAND: uv run python3 scripts/orchestrator.py run --task '%s' --providers qwen,claude\n" \
    "${PROMPT//\'/\'\\\'\'}" >&2
fi

log_event block "$REASON" "$CURRENT_PRESSURE"
exit 2
