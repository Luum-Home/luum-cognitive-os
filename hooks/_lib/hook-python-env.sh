#!/usr/bin/env bash
# SCOPE: both
# hook-python-env.sh — single source of truth for hook lib path.
# Sourced by the timing wrapper (Claude) and by the Codex command prefix.
# Exports PYTHONPATH so hooks that `from lib.<mod> import ...` resolve against
# the projected .cognitive-os/lib/ package. Idempotent: no-op if already present.
_cos_proj="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$PWD}}}"
case ":${PYTHONPATH:-}:" in
  *":$_cos_proj/.cognitive-os:"*) : ;;
  *) export PYTHONPATH="$_cos_proj/.cognitive-os${PYTHONPATH:+:$PYTHONPATH}" ;;
esac
