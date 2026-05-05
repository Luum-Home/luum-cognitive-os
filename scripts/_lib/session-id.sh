#!/usr/bin/env bash
# Shared session identity resolution for edit-lock coordination scripts.

cos_session_id() {
  if [ -n "${COGNITIVE_OS_SESSION_ID:-}" ]; then printf '%s' "$COGNITIVE_OS_SESSION_ID"; return; fi
  if [ -n "${CODEX_SESSION_ID:-}" ]; then        printf '%s' "$CODEX_SESSION_ID";        return; fi
  if [ -n "${CLAUDE_SESSION_ID:-}" ]; then       printf '%s' "$CLAUDE_SESSION_ID";       return; fi
  printf 'shell-%s' "${PPID:-$$}"
}
