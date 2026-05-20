#!/usr/bin/env bash
# SCOPE: both
# ADR-215 gitleaks wrapper. Keeps scanner as a subprocess dependency.
set -euo pipefail
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
if ! command -v gitleaks >/dev/null 2>&1; then
  echo '{"scanner":"gitleaks","status":"missing"}'
  exit 0
fi
exec gitleaks detect --source "$PROJECT_DIR" --redact --no-git "$@"
