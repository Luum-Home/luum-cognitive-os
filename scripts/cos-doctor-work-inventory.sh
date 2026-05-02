#!/usr/bin/env bash
# SCOPE: both
# Read-only projectable checklist for branches, worktrees, stashes, and dirty WIP.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/cos_work_inventory.py" "$@"
