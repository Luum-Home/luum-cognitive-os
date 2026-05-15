#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_ROOT="${TMPDIR:-/tmp}/cos-consumer-sdd-demo.$$"
PROJECT="$TMP_ROOT/project"
COS_BIN="$TMP_ROOT/cos"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

mkdir -p "$PROJECT"
cat > "$PROJECT/cognitive-os.yaml" <<'YAML'
project:
  name: consumer-sdd-demo
  phase: reconstruction
YAML

(
  cd "$ROOT/cmd/cos"
  go build -o "$COS_BIN" .
)

cd "$PROJECT"
"$COS_BIN" sdd next --feature cli_recent --title "CLI recent" --work-class medium
"$COS_BIN" sdd approve cli_recent
"$COS_BIN" sdd apply cli_recent

cat > .cognitive-os/workflows/sdd/cli_recent/design.md <<'MD'
# Design

## Files To Touch

- src/cli.py
- tests/test_cli.py

## Boundaries Not To Touch

- secrets/
- .env
MD

cat > .cognitive-os/workflows/sdd/cli_recent/tasks.md <<'MD'
# Tasks

- [x] Implement R1 within the design boundary.
- [x] Add or update evidence for R2.
- [x] Update traceability.md with every requirement-to-test/proof mapping.
MD

cat > .cognitive-os/workflows/sdd/cli_recent/traceability.md <<'MD'
# Traceability

| Requirement | Evidence | Status | Notes |
|---|---|---|---|
| R1 | tests/test_cli.py::test_recent_lists_notes | PASS | behavior test |
| R2 | MANUAL-PROOF: reviewer inspected command output transcript | ACCEPTED | local demo proof |
MD

"$COS_BIN" sdd review cli_recent
"$COS_BIN" sdd status --json > "$TMP_ROOT/status.json"

test -f .cognitive-os/workflows/sdd/cli_recent/requirements.md
test -f .cognitive-os/workflows/sdd/cli_recent/design.md
test -f .cognitive-os/workflows/sdd/cli_recent/tasks.md
test -f .cognitive-os/workflows/sdd/cli_recent/traceability.md
test -f .cognitive-os/workflows/sdd/cli_recent/review.md
test -f .cognitive-os/workflows/sdd/progress/history.md
python3 - "$TMP_ROOT/status.json" <<'PY'
import json
import sys
from pathlib import Path
state = json.loads(Path(sys.argv[1]).read_text())
assert state["features"]["cli_recent"]["status"] == "done", state
PY

echo "CONSUMER_SDD_DEMO: PASS project=$PROJECT"
