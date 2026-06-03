#!/usr/bin/env bash
# SCOPE: both
# Wrapper that runs the snake_case Python implementation.
# Passes all arguments through so callers can add --json, --project-dir, etc.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -z "${PYTHON_BIN:-}" ]; then
  if [ -n "${PYTHON:-}" ]; then
    PYTHON_BIN="$PYTHON"
  elif [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi
exec "$PYTHON_BIN" "${SCRIPT_DIR}/cos_coordination_status.py" "$@"
