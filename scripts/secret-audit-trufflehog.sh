#!/usr/bin/env bash
# SCOPE: both
# ADR-215 trufflehog wrapper. Keeps AGPL scanner isolated as CLI-only.
set -euo pipefail
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
if ! command -v trufflehog >/dev/null 2>&1; then
  echo '{"scanner":"trufflehog","status":"missing"}'
  exit 0
fi
exec trufflehog filesystem "$PROJECT_DIR" --json "$@"
