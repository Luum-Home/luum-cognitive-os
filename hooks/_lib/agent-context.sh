#!/usr/bin/env bash
# SCOPE: both
# Shared agent-context detection for destructive-operation blockers.

cos_is_agent_context() {
  [ -n "${CLAUDE_AGENT_ID:-}" ]             && return 0
  [ -n "${COGNITIVE_OS_SESSION_ID:-}" ]     && return 0
  [ "${ORCHESTRATOR_MODE:-}" = "executor" ] && return 0
  local ppid_name
  ppid_name=$(ps -p "$PPID" -o comm= 2>/dev/null || true)
  if echo "$ppid_name" | grep -qiE '^claude(-code)?$'; then
    return 0
  fi
  return 1
}
