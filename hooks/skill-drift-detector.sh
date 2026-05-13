#!/usr/bin/env bash
# SCOPE: os-only
# SessionStart hook: Skill Registry Runtime Drift Detector
#
# Compares on-disk SHA-256 hashes of locked skill files against
# skills/REGISTRY.lock. Emits a warning to stderr when drift is detected.
# Never blocks session start unless COS_SKILL_DRIFT_POLICY=block is set.
#
# See: docs/02-Decisions/adrs/ADR-285-skill-registry-runtime-drift-detection.md
#
# Budget: <50ms on warm mtime cache (stat-only pass for unchanged files).
# Killswitch: COS_DISABLE_SKILL_DRIFT_DETECTOR=1 — skip immediately.

set -uo pipefail

# Killswitch
if [ "${COS_DISABLE_SKILL_DRIFT_DETECTOR:-}" = "1" ]; then
  exit 0
fi

# ADR-028 §584: respect killswitch flag for non-critical hooks.
KILLSWITCH_LIB="$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
if [ -f "$KILLSWITCH_LIB" ]; then
  # shellcheck disable=SC1090
  source "$KILLSWITCH_LIB" 2>/dev/null || true
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"

LOCK_FILE="$PROJECT_DIR/skills/REGISTRY.lock"

# Fast exit if lock file doesn't exist — nothing to check.
if [ ! -f "$LOCK_FILE" ]; then
  exit 0
fi

# Run the Python detector. Errors in the detector are non-fatal.
if ! command -v python3 >/dev/null 2>&1; then
  echo "[skill-drift-detector] python3 not found — skipping drift check." >&2
  exit 0
fi

cd "$PROJECT_DIR" && python3 -c "
import sys
sys.path.insert(0, '.')
from lib.skill_drift_detector import main
main()
" 2>&1 || true

exit 0
