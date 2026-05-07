#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
PYTHONPATH="$ROOT" python3 - "$TMPDIR" <<'PY'
from pathlib import Path
import sys
from lib.handoff_envelope import HandoffEnvelope
from lib.handoff_dispatcher import HandoffCycleDetected, HandoffDispatcher

project = Path(sys.argv[1])
dispatcher = HandoffDispatcher(project_dir=project, session_id="smoke")
first = HandoffEnvelope.create(parent_event_seq=0, from_agent="A", to_agent="B", call_chain=["A"])
result = dispatcher.dispatch(first)
try:
    dispatcher.dispatch(result.envelope.next_hop(to_agent="A"))
except HandoffCycleDetected:
    print("cycle detected")
else:
    raise SystemExit("expected HandoffCycleDetected")
PY
