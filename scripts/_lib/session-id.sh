#!/usr/bin/env bash
# SCOPE: both
# Shared session identity resolution for edit-lock coordination scripts.
#
# Marked explicitly because it ships: cos_init installs it beside edit-coop.sh
# under .cognitive-os/bin/_lib/ so that every participant in a lock -- the
# hooks and the CLI they call -- resolves the SAME session identity. Without
# it each side falls back to its own default (shell-$PPID here,
# default-session in edit-coop.sh) and a lock taken by one is invisible to
# the other.
#
# The header is what makes this file travel: primitive-scope-overrides.yaml
# classifies scripts/_lib/** as os-only, but that manifest states header
# markers remain preferred, and primitive_scope_classifier honours an
# explicit marker over a glob fallback (see _override_for, the
# `declared is None or declared == override` guard).

cos_session_id() {
  if [ -n "${COGNITIVE_OS_SESSION_ID:-}" ]; then printf '%s' "$COGNITIVE_OS_SESSION_ID"; return; fi
  if [ -n "${CODEX_SESSION_ID:-}" ]; then        printf '%s' "$CODEX_SESSION_ID";        return; fi
  if [ -n "${CLAUDE_SESSION_ID:-}" ]; then       printf '%s' "$CLAUDE_SESSION_ID";       return; fi
  printf 'shell-%s' "${PPID:-$$}"
}
