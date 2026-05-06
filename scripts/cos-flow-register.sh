#!/usr/bin/env bash
# SCOPE: os-only
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$("$SCRIPT_DIR/cos-root" project)"
exec python3 "$ROOT/scripts/cos_flow_register.py" --project-dir "$ROOT" "$@"
