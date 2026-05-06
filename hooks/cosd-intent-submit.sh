#!/usr/bin/env bash
# SCOPE: os-only
# ADR-184: submit critical-surface intents to the local cosd arbiter.
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${DISABLE_HOOK_COSD_INTENT_SUBMIT:-0}" == "1" ]]; then
  exit 0
fi

# Lifecycle registration may invoke this hook without workflow arguments; the
# workflow-facing contract is explicit `submit-intent ...`, so no-arg runs are
# advisory no-ops.
if [[ "$#" -eq 0 ]]; then
  exit 0
fi

exec python3 "$SCRIPT_DIR/scripts/cos_daemon.py" --project-dir "$PROJECT_DIR" "$@"
