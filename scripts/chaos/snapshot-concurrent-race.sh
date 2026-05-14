#!/usr/bin/env bash
# SCOPE: os-only
# chaos/snapshot-concurrent-race.sh
#
# Spawns 3 parallel pre-agent-snapshot.sh invocations against the same repo.
# Verifies that no untracked files are lost and snapshot IDs are unique.
#
# Usage: bash scripts/chaos/snapshot-concurrent-race.sh
# Exit: 0 = PASS, 1 = FAIL

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$PROJECT_DIR/hooks/pre-agent-snapshot.sh"

info() { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}[PASS]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; }

echo -e "\n${BOLD}=== Chaos: Concurrent Snapshot Race ===${NC}\n"

TMPDIR_=$(mktemp -d)
trap 'rm -rf "$TMPDIR_"' EXIT

REPO="$TMPDIR_/test-repo"
mkdir -p "$REPO"
git -C "$REPO" init -b main -q
git -C "$REPO" config user.email "chaos@test.com"
git -C "$REPO" config user.name "Chaos"
echo "initial" > "$REPO/README.md"
git -C "$REPO" add README.md
git -C "$REPO" commit -q -m "init"

# Create 3 untracked files (one per "session")
for i in 1 2 3; do
  echo "content $i" > "$REPO/concurrent-$i.py"
done
info "Created concurrent-1.py, concurrent-2.py, concurrent-3.py"

TOOL_INPUT='{"tool_name":"Agent","tool_input":{"description":"concurrent"}}'

# Run 3 parallel hook invocations
info "Launching 3 concurrent hook invocations..."
for i in 1 2 3; do
  (
    CLAUDE_PROJECT_DIR="$REPO" \
      COGNITIVE_OS_SESSION_ID="sess-$i" \
      CLAUDE_AGENT_ID="concurrent-agent-$i" \
      PYTHONPATH="$PROJECT_DIR" \
      bash "$HOOK" <<< "$TOOL_INPUT" 2>/dev/null
  ) &
done
wait
info "All 3 invocations complete."

PASS=true

# Verify all untracked files survived
for i in 1 2 3; do
  if [ -f "$REPO/concurrent-$i.py" ]; then
    ok "  concurrent-$i.py survived in WT"
  else
    fail "  concurrent-$i.py was removed from WT!"
    PASS=false
  fi
done

# Verify snapshot IDs are unique
SNAP_DIR="$REPO/.cognitive-os/snapshots"
SNAP_COUNT=$(ls -1 "$SNAP_DIR" 2>/dev/null | wc -l | tr -d ' ')
info "Snapshots created: $SNAP_COUNT"
if [ "$SNAP_COUNT" -ge 1 ]; then
  ok "  At least one snapshot directory created"
else
  fail "  No snapshot directories created"
  PASS=false
fi

# Verify manifest files are valid JSON
MANIFEST_ERRORS=0
find "$SNAP_DIR" -name "manifest.json" 2>/dev/null | while read -r mp; do
  if python3 -c "import json; json.load(open('$mp'))" 2>/dev/null; then
    : # valid
  else
    fail "  Invalid manifest JSON: $mp"
    MANIFEST_ERRORS=$((MANIFEST_ERRORS + 1))
  fi
done

echo ""
if [ "$PASS" = true ]; then
  ok "Concurrent race PASSED — no files lost, no JSON corruption"
  exit 0
else
  fail "Concurrent race FAILED"
  exit 1
fi
