#!/usr/bin/env bash
# SCOPE: both
# PreToolUse hook: Skill Router Bash Gate
#
# Uses lib/skill_router.py to detect shell commands that bypass a mandatory
# maintenance skill. Advisory for generic matches; blocks dependency upgrades
# that should go through /deps-update so the SO records audit/apply intent.

set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
_HOOK_NAME="skill-router-bash-gate"
source "$(dirname "$0")/_lib/common.sh"

check_capability_level "skill-router-bash-gate"
check_disabled_env "skill-router-bash-gate"
check_private_mode

read_stdin_json
TOOL_NAME=$(stdin_field '.tool_name' '')
[ "$TOOL_NAME" = "Bash" ] || exit 0

COMMAND=$(stdin_field '.tool_input.command' '')
[ -n "$COMMAND" ] || exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$_PROJECT_DIR}}"

# Explicit operator override. Kept intentionally noisy so bypasses are auditable.
if printf '%s' "$COMMAND" | grep -q 'COS_ALLOW_SKILL_BYPASS=1'; then
  exit 0
fi

# Dependency/package manager mutations must go through /deps-update. This is
# the concrete high-ROI bypass class discovered during the hook-wiring audit:
# direct brew/pip/uv/npm/go upgrade commands skip dependency audit, engram
# symlink repair, and major-version review.
if printf '%s' "$COMMAND" | grep -Eqi '(^|[;&|[:space:]])(brew[[:space:]]+(upgrade|install)[[:space:]]+.*engram|brew[[:space:]]+upgrade|pip[0-9.]*[[:space:]]+install[[:space:]]+(-U|--upgrade)|uv[[:space:]]+(sync[[:space:]]+--upgrade|pip[[:space:]]+install[[:space:]]+.*(--upgrade|-U))|npm[[:space:]]+(update|upgrade)|pnpm[[:space:]]+(update|upgrade)|yarn[[:space:]]+(upgrade|up)|go[[:space:]]+get[[:space:]].*@)' ; then
  cat >&2 <<'MSG'
SKILL ROUTER BASH GATE: BLOCK
Direct dependency/toolchain upgrade command detected. Use `/deps-update --audit`
then `bash scripts/deps-update.sh --apply` (or documented manual review) so
Python package gaps, engram PATH symlinks, Docker images, and major bumps are
tracked together.

Override only with explicit operator intent: prefix command with COS_ALLOW_SKILL_BYPASS=1.
MSG
  exit 2
fi

# Best-effort generic skill suggestion. Never blocks: if Python/router/catalog is
# unavailable, the hook degrades silently.
if command -v python3 >/dev/null 2>&1 && [ -f "$PROJECT_DIR/lib/skill_router.py" ]; then
  SUGGESTION=$(PROJECT_DIR="$PROJECT_DIR" python3 - "$COMMAND" <<'PYEOF' 2>/dev/null || true
import os
import sys
from pathlib import Path

project = Path(os.environ.get("PROJECT_DIR", "."))
sys.path.insert(0, str(project))
try:
    from lib.skill_router import SkillRouter
except Exception:
    raise SystemExit(0)

cmd = sys.argv[1]
router = SkillRouter(project_root=project)
match = router.best_match(cmd)
if match and match.confidence >= 0.85:
    print(f"SKILL ROUTER: command resembles {match.invoke_command} ({match.confidence:.2f}) — consider using the skill workflow before raw Bash.")
PYEOF
)
  [ -n "$SUGGESTION" ] && echo "$SUGGESTION" >&2
fi

exit 0
