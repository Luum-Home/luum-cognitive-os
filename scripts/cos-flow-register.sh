#!/usr/bin/env bash
# SCOPE: os-only
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
exec python3 "$ROOT/scripts/cos_flow_register.py" --project-dir "$ROOT" "$@"
