#!/usr/bin/env bash
# SCOPE: os-only
# lineage-relaunch-gate.sh — Stop hook: decide whether a successor session runs.
#
# Piece 3 of three, and the most dangerous file in this repository. The
# evaluator already existed (goal-stop-gate.sh, 337 runs); what was missing was
# the step that ACTS on its verdict. This is that step, and it is off.
#
# OFF BY DEFAULT, AND OFF AS A DECISION:
#   The launch path is gated on an arm file that no code in this repo creates
#   on its own. `scripts/cos_lineage.py arm --goal-id <id>` writes it, an
#   operator runs that, and it expires. A freshly cloned repo cannot reach
#   scripts/cos_relaunch.py at all: this hook returns before naming it.
#   That is deliberately not the same thing as "the directory does not exist" —
#   directories appear the first time anything touches them.
#
# KILL-SWITCH — and the trap this repo already paid for once:
#   COS_DISABLE_AUTONOMOUS_RELAUNCH=1 only works when the harness inherits it,
#   i.e. `export COS_DISABLE_AUTONOMOUS_RELAUNCH=1` before launching claude, or
#   the `env` block of .claude/settings.json. A `VAR=1 <command>` prefix typed
#   inside a session does NOT reach any hook: the hook is a child of the
#   harness, not of the Bash tool's shell. See the long comment in
#   hooks/protected-config-write-guard.sh:48 for the incident that taught this.
#   Because the default is disarmed, the env var is the second switch, not the
#   first one.
#
# NEVER BLOCKS THE STOP. Whatever it decides, the operator's session ends. It
# also never kills anything: cos_relaunch.py records the child PID in
# .cognitive-os/lineage/decisions.jsonl and stopping a run is the operator's
# call, made with that PID.

set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

if [ "${DISABLE_HOOK_LINEAGE_RELAUNCH_GATE:-}" = "true" ]; then
  exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}}"
ARM_FILE="$PROJECT_DIR/.cognitive-os/lineage/autonomy.enabled"

INPUT="$(cat 2>/dev/null || true)"

# ── Gate 0: the switch. Everything below this line is unreachable while the
# arm file is absent, including the name of the launcher. ────────────────────
if [ ! -f "$ARM_FILE" ]; then
  exit 0
fi

if [ "${COS_DISABLE_AUTONOMOUS_RELAUNCH:-}" = "1" ]; then
  exit 0
fi

command -v python3 >/dev/null 2>&1 || exit 0

SESSION_ID=""
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null || true)"
fi
[ -z "$SESSION_ID" ] && SESSION_ID="${CLAUDE_SESSION_ID:-}"
[ -z "$SESSION_ID" ] && exit 0

# ── Ask the goal state what it thinks. No goal, or a finished one, means
# there is nothing to continue and therefore nothing to launch. ─────────────
GOAL_INFO="$(python3 - "$PROJECT_DIR" <<'PYEOF' 2>/dev/null || true
import sys
from pathlib import Path
project_dir = Path(sys.argv[1])
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))
try:
    from cos_lib.goal_state import GoalStateStore, _ALLOW_STOP_STATUSES
except Exception:
    sys.exit(0)
import os
store = GoalStateStore(
    base_dir=project_dir / ".cognitive-os" / "goals",
    workspace_thread_id=os.environ.get("COS_WORKSPACE_THREAD_ID", "default"),
)
goal = store.load()
if goal is None or goal.status in _ALLOW_STOP_STATUSES:
    sys.exit(0)
print(f"{goal.goal_id}\t{getattr(goal, 'consecutive_no_progress', 0)}")
PYEOF
)"

[ -z "$GOAL_INFO" ] && exit 0

GOAL_ID="${GOAL_INFO%%$'\t'*}"
NO_PROGRESS="${GOAL_INFO##*$'\t'}"
case "$NO_PROGRESS" in ''|*[!0-9]*) NO_PROGRESS=0 ;; esac

# ── Decide and, only on a clear verdict, launch. cos_relaunch.py re-checks
# every fuse and reserves its slot under a lock before spawning. ────────────
python3 "$PROJECT_DIR/scripts/cos_relaunch.py" \
  --project-dir "$PROJECT_DIR" \
  --session-id "$SESSION_ID" \
  --goal-id "$GOAL_ID" \
  --no-progress "$NO_PROGRESS" \
  >/dev/null 2>&1 || true

exit 0
