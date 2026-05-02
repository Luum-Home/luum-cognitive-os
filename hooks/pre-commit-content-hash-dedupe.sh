#!/usr/bin/env bash
# SCOPE: both
# pre-commit-content-hash-dedupe.sh — P4.1 (ADR-116)
#
# Pre-commit hook that detects when the staged diff matches a commit already
# present on origin/main, preventing accidental duplicate commits from
# parallel sessions.
#
# Uses `git patch-id --stable` to fingerprint the staged content and
# compares against recent commits on origin/main.
#
# Environment variables:
#   COS_DEDUPE_MODE   — warn (default) | block | off
#   COS_DEDUPE_DEPTH  — number of origin/main commits to scan (default: 200)
#
# Exit codes:
#   0 — no collision (commit allowed)
#   2 — collision detected in block mode (commit blocked)
#
# Emits a conflict_detected event to .cognitive-os/sessions/events.jsonl
# via lib/event_bus.py when a collision is found.
set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Off by default at the hook level when the env var is explicitly set to off.
COS_DEDUPE_MODE="${COS_DEDUPE_MODE:-warn}"

if [ "$COS_DEDUPE_MODE" = "off" ]; then
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "[dedupe] WARNING: python3 not found, skipping content-hash dedupe check" >&2
  exit 0
fi

DEDUPE_SCRIPT="$ROOT_DIR/scripts/precommit_content_hash.py"

if [ ! -f "$DEDUPE_SCRIPT" ]; then
  echo "[dedupe] WARNING: $DEDUPE_SCRIPT not found, skipping check" >&2
  exit 0
fi

python3 "$DEDUPE_SCRIPT"
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 2 ]; then
  exit 2
fi

exit 0
