#!/usr/bin/env bash
# SCOPE: both
# Wrapper that runs the snake_case Python implementation.
# Passes all arguments through so callers can add --json, --project-dir, etc.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/cos_coordination_status.py" "$@"
