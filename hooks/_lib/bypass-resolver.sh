#!/usr/bin/env bash
# ADR-241 shared bypass resolver.
# Usage: source this file, then call `cos_bypass_allows <stable-key>`.
# Stable keys are read from COS_BYPASS (comma-separated) and from the optional
# runtime file .cognitive-os/runtime/bypass.env. Legacy env aliases remain for
# one release and are centralized here.

_cos_bypass_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

_cos_bypass_project_dir() {
  printf '%s' "${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
}

_cos_bypass_combined_list() {
  local project_dir runtime_file runtime_value
  project_dir="$(_cos_bypass_project_dir)"
  runtime_file="$project_dir/.cognitive-os/runtime/bypass.env"
  runtime_value=""
  if [ -f "$runtime_file" ]; then
    runtime_value="$(grep -E '^COS_BYPASS=' "$runtime_file" 2>/dev/null | tail -1 | sed 's/^COS_BYPASS=//' | tr -d '"' | tr -d "'")"
  fi
  printf '%s,%s' "${COS_BYPASS:-}" "$runtime_value"
}

_cos_bypass_list_contains() {
  local key="$1" item list
  list="$(_cos_bypass_combined_list)"
  IFS=',' read -r -a _cos_bypass_items <<< "$list"
  for item in "${_cos_bypass_items[@]}"; do
    item="$(printf '%s' "$item" | xargs 2>/dev/null || printf '%s' "$item")"
    [ "$item" = "$key" ] && return 0
  done
  return 1
}

_cos_bypass_legacy_alias_allows() {
  local key="$1"
  case "$key" in
    destructive_git)
      _cos_bypass_truthy "${COS_ALLOW_DESTRUCTIVE_GIT:-}" || _cos_bypass_truthy "${COS_GIT_BYPASS:-}"
      ;;
    main_branch_write)
      _cos_bypass_truthy "${COS_ALLOW_MAIN_BRANCH_WRITE:-}" || _cos_bypass_truthy "${COS_ALLOW_DIRECT_MAIN:-}"
      ;;
    branch_switch)
      _cos_bypass_truthy "${COS_ALLOW_BRANCH_SWITCH:-}"
      ;;
    reset_over_wip)
      _cos_bypass_truthy "${COS_ALLOW_RESET_OVER_WIP:-}"
      ;;
    commit_guard)
      _cos_bypass_truthy "${COS_BYPASS_COMMIT_GUARD:-}"
      ;;
    branch_ownership)
      _cos_bypass_truthy "${COS_ALLOW_BRANCH_OWNERSHIP_OVERRIDE:-}"
      ;;
    claim_gate)
      [ "${COS_ORCHESTRATOR_CLAIM_GATE_MODE:-}" = "warn" ] || _cos_bypass_truthy "${DISABLE_HOOK_ORCHESTRATOR_CLAIM_GATE:-}"
      ;;
    push_collision)
      _cos_bypass_truthy "${DISABLE_HOOK_PUSH_COLLISION_CHECK:-}"
      ;;
    direct_push)
      _cos_bypass_truthy "${COS_ALLOW_DIRECT_PUSH:-}"
      ;;
    direct_main)
      _cos_bypass_truthy "${COS_ALLOW_DIRECT_MAIN:-}"
      ;;
    unproven_scope_both)
      _cos_bypass_truthy "${COS_ALLOW_UNPROVEN_SCOPE_BOTH:-}"
      ;;
    *) return 1 ;;
  esac
}

cos_bypass_allows() {
  local key="$1"
  [ -n "$key" ] || return 1
  _cos_bypass_list_contains "$key" && return 0
  _cos_bypass_legacy_alias_allows "$key" && return 0
  return 1
}
