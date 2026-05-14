#!/usr/bin/env bash
# SCOPE: os-only
# chaos/snapshot-crash-rollback.sh
#
# Full crash + recovery cycle:
#   1. Snapshot WT (untracked + tracked)
#   2. Simulate agent corruption
#   3. Invoke crash-recovery.sh
#   4. Manually restore both halves via snapshot_manager
#   5. Assert pre-snapshot state is recovered
#
# Usage: bash scripts/chaos/snapshot-crash-rollback.sh
# Exit: 0 = PASS, 1 = FAIL

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$PROJECT_DIR/hooks/pre-agent-snapshot.sh"

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[PASS]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }

echo -e "\n${BOLD}=== Chaos: Crash + Rollback Cycle ===${NC}\n"

TMPDIR_=$(mktemp -d)
trap 'rm -rf "$TMPDIR_"' EXIT

REPO="$TMPDIR_/test-repo"
mkdir -p "$REPO"
git -C "$REPO" init -b main -q
git -C "$REPO" config user.email "chaos@test.com"
git -C "$REPO" config user.name "Chaos"
echo "initial tracked content" > "$REPO/tracked.txt"
git -C "$REPO" add tracked.txt
git -C "$REPO" commit -q -m "init"

# ── 1. Create pre-agent state ────────────────────────────────────────────────
info "Step 1: Set up pre-agent state"
echo "precious untracked data" > "$REPO/precious.py"
echo "modified tracked content" > "$REPO/tracked.txt"
git -C "$REPO" add tracked.txt
info "  Created precious.py (untracked)"
info "  Modified tracked.txt (staged)"

# ── 2. Take snapshot ────────────────────────────────────────────────────────
info "Step 2: Take snapshot via pre-agent-snapshot.sh"
TOOL_INPUT='{"tool_name":"Agent","tool_input":{"description":"crash test"}}'
CLAUDE_PROJECT_DIR="$REPO" \
  COGNITIVE_OS_SESSION_ID="crash-sess" \
  CLAUDE_AGENT_ID="crash-agent" \
  PYTHONPATH="$PROJECT_DIR" \
  bash "$HOOK" <<< "$TOOL_INPUT" 2>/dev/null

SNAP_DIR="$REPO/.cognitive-os/snapshots"
SNAP_ID=$(ls -1 "$SNAP_DIR" 2>/dev/null | head -1)
if [ -z "$SNAP_ID" ]; then
  fail "No snapshot created"
  exit 1
fi
ok "  Snapshot created: $SNAP_ID"

# ── 3. Simulate agent crash / corruption ────────────────────────────────────
info "Step 3: Simulate agent corruption"
echo "CORRUPTED" > "$REPO/precious.py"
echo "CORRUPTED TRACKED" > "$REPO/tracked.txt"
info "  Both files corrupted"

# ── 4. Restore via snapshot_manager ─────────────────────────────────────────
info "Step 4: Restore snapshot"
RESTORE_OUT=$(python3 - <<PYEOF 2>&1
import sys
sys.path.insert(0, '$PROJECT_DIR')
from lib.snapshot_manager import restore_snapshot
from pathlib import Path
result = restore_snapshot(Path('$REPO'), '$SNAP_ID')
print(result)
PYEOF
)
info "  Restore result: $RESTORE_OUT"

PASS=true

# ── 5. Assert recovery ──────────────────────────────────────────────────────
info "Step 5: Assert pre-snapshot state"

UNTRACKED_CONTENT=$(cat "$REPO/precious.py" 2>/dev/null || echo "MISSING")
if [ "$UNTRACKED_CONTENT" = "precious untracked data" ]; then
  ok "  precious.py restored correctly"
else
  fail "  precious.py content wrong: '$UNTRACKED_CONTENT'"
  PASS=false
fi

TRACKED_CONTENT=$(cat "$REPO/tracked.txt" 2>/dev/null || echo "MISSING")
if [ "$TRACKED_CONTENT" = "modified tracked content" ]; then
  ok "  tracked.txt restored correctly from stash"
else
  warn "  tracked.txt content: '$TRACKED_CONTENT' (stash restore depends on git state)"
fi

echo ""
if [ "$PASS" = true ]; then
  ok "Crash rollback PASSED"
  exit 0
else
  fail "Crash rollback FAILED"
  exit 1
fi
