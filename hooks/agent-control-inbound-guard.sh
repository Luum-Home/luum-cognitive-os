#!/usr/bin/env bash
# SCOPE: both
# Blocks hook-capable harnesses at tool/action boundaries when an inbound
# Agent Bus control signal says stop or pause. This is the portable enforcement
# path for harnesses where Cognitive OS does not own a child process handle.

set -uo pipefail

if [[ "${DISABLE_HOOK_AGENT_CONTROL_INBOUND_GUARD:-0}" == "1" || "${DISABLE_HOOK_AGENT_CONTROL_INBOUND_GUARD:-}" == "true" ]]; then
  exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COS_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
INPUT="$(cat 2>/dev/null || true)"

OUT_FILE="${TMPDIR:-/tmp}/cos-agent-control-policy.$$.$RANDOM.out"
ERR_FILE="${TMPDIR:-/tmp}/cos-agent-control-policy.$$.$RANDOM.err"
trap 'rm -f "$OUT_FILE" "$ERR_FILE"' EXIT

PYTHONPATH="$COS_ROOT:${PYTHONPATH:-}" COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" \
python3 - "$PROJECT_DIR" "$INPUT" <<'PY' >"$OUT_FILE" 2>"$ERR_FILE" || true
from __future__ import annotations

import json
import sys
from pathlib import Path

from lib.agent_control_policy import append_policy_event, evaluate_control

project = Path(sys.argv[1])
raw = sys.argv[2] if len(sys.argv) > 2 else ""
try:
    payload = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    payload = {}

decision = evaluate_control(project, payload=payload)
if decision.should_block:
    append_policy_event(project, decision)
    print(json.dumps(decision.to_dict(), sort_keys=True))
PY

if [[ -s "$OUT_FILE" ]]; then
  DECISION="$(cat "$OUT_FILE")"
  COMMAND="$(python3 - <<'PY' "$DECISION" 2>/dev/null || printf unknown
import json, sys
print(json.loads(sys.argv[1]).get("command", "unknown"))
PY
)"
  echo "agent-control-inbound-guard: blocked by inbound ${COMMAND} control signal." >&2
  echo "$DECISION" >&2
  exit 2
fi

exit 0
