#!/usr/bin/env bash
# SCOPE: os-only
# PreToolUse hook: Skill Router Bash Gate
#
# Uses lib/skill_router.py to detect shell commands that bypass a mandatory
# maintenance skill. Advisory for generic matches; blocks dependency upgrades
# that should go through /deps-update so the SO records audit/apply intent.

set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
_HOOK_NAME="skill-router-bash-gate"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"
source "$(dirname "$0")/_lib/primitive-intervention.sh"

check_capability_level "skill-router-bash-gate"
check_disabled_env "skill-router-bash-gate"
check_private_mode

read_stdin_json
TOOL_NAME=$(stdin_field '.tool_name' '')
[ "$TOOL_NAME" = "Bash" ] || exit 0

COMMAND=$(stdin_field '.tool_input.command' '')
[ -n "$COMMAND" ] || exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$_PROJECT_DIR}}"
METRICS_DIR="$(_resolve_metrics_dir)"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Explicit operator override. Kept intentionally noisy so bypasses are auditable.
if printf '%s' "$COMMAND" | grep -q 'COS_ALLOW_SKILL_BYPASS=1'; then
  exit 0
fi

# ADR-214: Tool Discovery Pre-Use Gate. Before falling back to generic skill
# suggestions, block known ad-hoc tool choices when this repository already has
# a canonical primitive/toolchain for the task. This is deliberately wired into
# the existing Bash gate so Bash launch paths get one cohesive skill/tool-use
# preflight instead of another parallel hook to drift.
if [ "${COS_ALLOW_TOOL_DISCOVERY_BYPASS:-0}" != "1" ] \
   && ! printf '%s' "$COMMAND" | grep -q 'COS_ALLOW_TOOL_DISCOVERY_BYPASS=1' \
   && command -v python3 >/dev/null 2>&1 \
   && [ -f "$PROJECT_DIR/lib/tool_discovery_preuse.py" ]; then
  TOOL_DISCOVERY_OUT=$(python3 "$PROJECT_DIR/scripts/cos-tool-discovery-preuse" \
    --project-dir "$PROJECT_DIR" --command "$COMMAND" 2>&1)
  TOOL_DISCOVERY_RC=$?
  if [ "$TOOL_DISCOVERY_RC" -eq 2 ]; then
    echo "TOOL DISCOVERY PRE-USE GATE: BLOCK" >&2
    echo "$TOOL_DISCOVERY_OUT" >&2
    echo "Override only with explicit operator intent: prefix command with COS_ALLOW_TOOL_DISCOVERY_BYPASS=1 and document why." >&2
    safe_jsonl_append "$METRICS_DIR/skill-routing.jsonl" \
      "{\"timestamp\":\"$TIMESTAMP\",\"primitive\":\"skill-router\",\"action\":\"BLOCK\",\"reason_code\":\"tool_discovery_bypass\",\"target_ref\":\"tool-discovery-preuse\"}"
    primitive_intervention_emit \
      "skill-router" \
      "hooks/skill-router-bash-gate.sh" \
      "block" \
      "tool_discovery_bypass" \
      "tool-discovery-preuse" \
      ".cognitive-os/metrics/skill-routing.jsonl" \
      "Bash"
    exit 2
  elif [ -n "$TOOL_DISCOVERY_OUT" ] && printf '%s' "$TOOL_DISCOVERY_OUT" | grep -q 'tool-discovery-preuse: warn'; then
    echo "$TOOL_DISCOVERY_OUT" >&2
    safe_jsonl_append "$METRICS_DIR/skill-routing.jsonl" \
      "{\"timestamp\":\"$TIMESTAMP\",\"primitive\":\"skill-router\",\"action\":\"WARN\",\"reason_code\":\"tool_discovery_bypass\",\"target_ref\":\"tool-discovery-preuse\"}"
    primitive_intervention_emit \
      "skill-router" \
      "hooks/skill-router-bash-gate.sh" \
      "warn" \
      "tool_discovery_bypass" \
      "tool-discovery-preuse" \
      ".cognitive-os/metrics/skill-routing.jsonl" \
      "Bash"
  fi
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
  safe_jsonl_append "$METRICS_DIR/skill-routing.jsonl" \
    "{\"timestamp\":\"$TIMESTAMP\",\"primitive\":\"skill-router\",\"action\":\"BLOCK\",\"reason_code\":\"dependency_update_bypass\",\"target_ref\":\"dependency-update-command\"}"
  primitive_intervention_emit \
    "skill-router" \
    "hooks/skill-router-bash-gate.sh" \
    "block" \
    "dependency_update_bypass" \
    "dependency-update-command" \
    ".cognitive-os/metrics/skill-routing.jsonl" \
    "Bash"
  exit 2
fi

# Best-effort generic skill suggestion. Never blocks: if Python/router/catalog is
# unavailable, the hook degrades silently. Disabled by default on the Bash hot
# path because loading the full semantic skill router on every shell command
# was a multi-second PreToolUse tax; UserPromptSubmit skill suggestions cover
# the normal discovery path. Re-enable for debugging with
# COS_SKILL_ROUTER_BASH_SUGGEST=1.
if [ "${COS_SKILL_ROUTER_BASH_SUGGEST:-0}" = "1" ] && command -v python3 >/dev/null 2>&1 && [ -f "$PROJECT_DIR/lib/skill_router.py" ]; then
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
  if [ -n "$SUGGESTION" ]; then
    echo "$SUGGESTION" >&2
    safe_jsonl_append "$METRICS_DIR/skill-routing.jsonl" \
      "{\"timestamp\":\"$TIMESTAMP\",\"primitive\":\"skill-router\",\"action\":\"SUGGEST\",\"reason_code\":\"skill_route_available\",\"target_ref\":\"skill-route-suggestion\"}"
    primitive_intervention_emit \
      "skill-router" \
      "hooks/skill-router-bash-gate.sh" \
      "suggest" \
      "skill_route_available" \
      "skill-route-suggestion" \
      ".cognitive-os/metrics/skill-routing.jsonl" \
      "Bash"
  fi
fi

exit 0
