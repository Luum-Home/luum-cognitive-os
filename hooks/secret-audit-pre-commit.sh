#!/usr/bin/env bash
# SCOPE: both
# ADR-215 pre-commit release-scope secret audit wrapper.
set -euo pipefail
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
SCRIPT="$PROJECT_DIR/scripts/cos-cross-stack-secret-audit"
[ -x "$SCRIPT" ] || exit 0
exec "$SCRIPT" --project-dir "$PROJECT_DIR" --release-scope --strict --json
