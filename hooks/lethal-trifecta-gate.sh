#!/usr/bin/env bash
# SCOPE: os-only
# PreToolUse hook: blocks private data + untrusted content + external communication.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/common.sh"
check_private_mode
check_disabled_env "lethal-trifecta-gate"

read_stdin_json
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
METRICS_DIR="$(resolve_session_dir)"
METRICS_FILE="$METRICS_DIR/lethal-trifecta.jsonl"

RESULT_JSON=$(PAYLOAD_JSON="$_STDIN_JSON" PYTHONPATH="$HOOK_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 - "$METRICS_FILE" <<'PY'
import json
import os
import sys
from lib.lethal_trifecta import classify_json
from lib.metric_event import MetricEvent, append_event

result = classify_json(os.environ.get("PAYLOAD_JSON", "{}"))
append_event(
    sys.argv[1],
    MetricEvent(
        source="lethal-trifecta-gate",
        event_type="security.lethal_trifecta",
        severity=result.get("severity", "info"),
        payload=result,
    ),
)
print(json.dumps(result, separators=(",", ":"), sort_keys=True))
PY
)

DECISION=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("decision", "allow"))' "$RESULT_JSON")
SCORE=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("score", 0))' "$RESULT_JSON")
REASONS=$(python3 -c 'import json,sys; print(", ".join(json.loads(sys.argv[1]).get("reasons", [])))' "$RESULT_JSON")

if [ "$DECISION" = "block" ]; then
  echo "=== LETHAL TRIFECTA GATE: BLOCKED ===" >&2
  echo "Risk score: $SCORE" >&2
  echo "Detected private data + untrusted content + external communication." >&2
  echo "Reasons: $REASONS" >&2
  echo "Action: isolate/sanitize untrusted content or ask for explicit approval before external communication." >&2
  exit 2
fi

if [ "$DECISION" = "warn" ]; then
  echo "=== LETHAL TRIFECTA GATE: WARNING ===" >&2
  echo "Risk score: $SCORE" >&2
  echo "Reasons: $REASONS" >&2
fi

exit 0
