#!/usr/bin/env bash
# SCOPE: both
# Wrapper that runs cos_work_inventory.py --all.
# Passes all arguments through so callers can add --json, --strict, etc.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/cos_work_inventory.py" --all "$@"
