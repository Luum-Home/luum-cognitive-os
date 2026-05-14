#!/usr/bin/env bash
# SCOPE: both
# ADR-186: last-in-chain UserPromptSubmit context-budget meter.

set -uo pipefail

if [[ "${DISABLE_HOOK_CONTEXT_BUDGET_METER:-0}" == "1" || "${DISABLE_HOOK_CONTEXT_BUDGET_METER:-}" == "true" ]]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COS_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}}"
INPUT="$(cat 2>/dev/null || true)"

python3 - "$PROJECT_DIR" "$COS_ROOT" "$SESSION_ID" "$INPUT" <<'PY'
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

start_ns = time.perf_counter_ns()
project = Path(sys.argv[1]).resolve()
cos_root = Path(sys.argv[2]).resolve()
session_id = sys.argv[3]
raw = sys.argv[4] if len(sys.argv) > 4 else ""
sys.path.insert(0, str(cos_root))
from lib.context_budget import append_metric, count_tokens, evaluate, read_budget

try:
    data = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    data = {}
prompt = ""
additional = ""
if isinstance(data, dict):
    prompt = str(data.get("prompt") or data.get("message") or "")
    hso = data.get("hookSpecificOutput") if isinstance(data.get("hookSpecificOutput"), dict) else {}
    additional = str(data.get("additionalContext") or hso.get("additionalContext") or "")
text = prompt + additional
used = count_tokens(text)
verdict = evaluate("user", used, read_budget(project / "cognitive-os.yaml"))
latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
row = {
    "schema_version": 1,
    "timestamp_epoch": time.time(),
    "session_id": session_id,
    "source": "context-budget-meter",
    "layer": "user",
    "prompt_chars": len(prompt),
    "additional_context_chars": len(additional),
    "total_chars": len(text),
    "tokens_estimate": used,
    "budget_token_max": verdict.budget_token_max,
    "ratio_used": round(verdict.ratio_used, 4),
    "verdict": verdict.verdict,
    "allowed": verdict.allowed,
    "reason": verdict.reason,
    "latency_ms": round(latency_ms, 3),
}
append_metric(project, row)
if verdict.verdict == "WARN":
    print(f"context-budget-meter: WARN user context {used}/{verdict.budget_token_max} tokens", file=sys.stderr)
elif verdict.verdict == "BLOCK" and not verdict.allowed:
    print(f"context-budget-meter: BLOCK user context {used}/{verdict.budget_token_max} tokens", file=sys.stderr)
    raise SystemExit(2)
PY
rc=$?
if [[ "$rc" -eq 2 ]]; then
  exit 2
fi
exit "$rc"
