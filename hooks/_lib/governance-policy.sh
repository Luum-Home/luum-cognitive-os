#!/usr/bin/env bash
# SCOPE: os-only
# Shared phase-aware governance policy adapter for blocking hooks.
# Return 0 when the current phase explicitly allows the category to hard-block.
# Return 1 when a known phase demotes the category to advisory.
# Fail open to existing hook behavior when the policy command/config is absent
# or the phase is unknown, so adoption never silently disables legacy safety.

cos_governance_policy_allows_block() {
  local category="$1"
  local project_dir="${PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}}"
  local script="$project_dir/scripts/cos"
  local payload phase allowed

  [ -x "$script" ] || return 0
  command -v python3 >/dev/null 2>&1 || return 0

  payload=$("$script" governance policy --project-dir "$project_dir" --category "$category" --json 2>/dev/null || true)
  [ -n "$payload" ] || return 0

  phase=$(printf '%s' "$payload" | python3 -c 'import json,sys; print((json.load(sys.stdin).get("phase") or "unknown"))' 2>/dev/null || echo unknown)
  [ "$phase" = "unknown" ] && return 0
  allowed=$(printf '%s' "$payload" | python3 -c 'import json,sys; print("true" if json.load(sys.stdin).get("allowed_to_block") else "false")' 2>/dev/null || echo true)
  [ "$allowed" = "true" ]
}

cos_governance_policy_advisory_message() {
  local hook_name="$1"
  local category="$2"
  echo "[$hook_name] ADVISORY: cos governance policy demoted category '$category' to warn-only in this project phase." >&2
}
