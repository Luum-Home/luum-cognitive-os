#!/usr/bin/env bash
# chaos/snapshot-vanishing-untracked.sh
#
# Reproduces the original ADR-099 bug and demonstrates the fix.
#
# With COS_LEGACY_SNAPSHOT=1: untracked file vanishes from WT (old bug).
# Without:                    untracked file survives (fix).
#
# Usage: bash scripts/chaos/snapshot-vanishing-untracked.sh
# Exit: 0 = PASS, 1 = FAIL

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$PROJECT_DIR/hooks/pre-agent-snapshot.sh"

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[PASS]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }

echo -e "\n${BOLD}=== Chaos: Vanishing Untracked Files ===${NC}\n"

# ── Setup temp repo ──────────────────────────────────────────────────────────
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

SCENARIO_PASS=true

# ── Scenario A: Legacy mode (COS_LEGACY_SNAPSHOT=1) — file should vanish ──
info "Scenario A: Legacy mode (COS_LEGACY_SNAPSHOT=1)"
echo "WIP content" > "$REPO/precious.py"
info "  Created untracked file: precious.py"

TOOL_INPUT='{"tool_name":"Agent","tool_input":{"description":"test"}}'
COS_LEGACY_SNAPSHOT=1 \
  CLAUDE_PROJECT_DIR="$REPO" \
  COGNITIVE_OS_SESSION_ID="chaos-session" \
  CLAUDE_AGENT_ID="chaos-agent-legacy" \
  PYTHONPATH="$PROJECT_DIR" \
  bash "$HOOK" <<< "$TOOL_INPUT" 2>/dev/null

if [ ! -f "$REPO/precious.py" ]; then
  ok "  [A] Legacy mode: file vanished (expected — old bug reproduced)"
else
  warn "  [A] Legacy mode: file survived (git may have noop'd on clean WT — check stash)"
fi

# Restore the file for scenario B
echo "WIP content" > "$REPO/precious.py"
git -C "$REPO" stash drop -q 2>/dev/null || true

# ── Scenario B: New mode (default) — file must survive ────────────────────
info "Scenario B: New mode (ADR-099, default)"
info "  Created untracked file: precious.py"

TOOL_INPUT='{"tool_name":"Agent","tool_input":{"description":"test"}}'
unset COS_LEGACY_SNAPSHOT 2>/dev/null || true
CLAUDE_PROJECT_DIR="$REPO" \
  COGNITIVE_OS_SESSION_ID="chaos-session" \
  CLAUDE_AGENT_ID="chaos-agent-new" \
  PYTHONPATH="$PROJECT_DIR" \
  bash "$HOOK" <<< "$TOOL_INPUT" 2>/dev/null

if [ -f "$REPO/precious.py" ]; then
  ok "  [B] New mode: file survived in WT"
else
  fail "  [B] New mode: file vanished — FIX BROKEN"
  SCENARIO_PASS=false
fi

# Check backup exists
SNAP_DIR="$REPO/.cognitive-os/snapshots"
BACKUP_COUNT=$(find "$SNAP_DIR" -name "precious.py" 2>/dev/null | wc -l | tr -d ' ')
if [ "$BACKUP_COUNT" -gt 0 ]; then
  ok "  [B] Backup copy exists in snapshot dir"
else
  fail "  [B] No backup copy found in snapshot dir"
  SCENARIO_PASS=false
fi

echo ""
if [ "$SCENARIO_PASS" = true ]; then
  ok "All scenarios PASSED"
  exit 0
else
  fail "One or more scenarios FAILED"
  exit 1
fi
