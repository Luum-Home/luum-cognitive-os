#!/usr/bin/env bash
# SCOPE: os-only
# completeness-check.sh — Compatibility entrypoint for level-5 completeness gating.
#
# Delegates to predev-completeness-check.sh after honoring model capability
# auto-disable rules for the canonical component name used by capability_levels.py.

set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HOOK_DIR/_lib/common.sh"
source "$HOOK_DIR/_lib/killswitch_check.sh"

check_capability_level "completeness-check"

exec "$HOOK_DIR/predev-completeness-check.sh"
