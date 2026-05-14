#!/usr/bin/env bash
# SCOPE: os-only
# @on-demand: advisory diagnostic; invoke manually when troubleshooting cos-status or missing .cognitive-os dir
# session-sanity.sh — Advisory session-state sanity check for cos-status references.

set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}}"

if [ -f "$PROJECT_DIR/cognitive-os.yaml" ] || [ -d "$PROJECT_DIR/.cognitive-os" ]; then
  exit 0
fi

echo "SESSION SANITY: no cognitive-os.yaml or .cognitive-os directory found under $PROJECT_DIR" >&2
exit 0
