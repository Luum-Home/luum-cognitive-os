#!/usr/bin/env bash
# SCOPE: os-only
# registration-check.sh — PreToolUse hook on Agent (advisory)
# CONCERNS: consistency, registration, os-development
#
# Warns when unregistered hooks/rules/skills/packages are detected.
# Only fires when working on the luum-agent-os repo itself (dogfooding).
#
# Exit codes:
#   0 — always (advisory only, never blocks)

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# ── Guard: only active inside the luum-agent-os repo itself ─────────────────
# Detect the OS repo by checking for hooks/self-install.sh
if [ ! -f "$PROJECT_DIR/hooks/self-install.sh" ]; then
  exit 0
fi

# ── Guard: require Python and the lib module ─────────────────────────────────
if ! command -v python3 &>/dev/null; then
  exit 0
fi

if [ ! -f "$PROJECT_DIR/lib/component_registry.py" ]; then
  exit 0
fi

# ── Run detection ────────────────────────────────────────────────────────────
RESULT=$(python3 - <<'PYEOF' 2>/dev/null
import sys, os
sys.path.insert(0, os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
from lib.component_registry import detect_all_unregistered, format_registration_report
report = detect_all_unregistered(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
if report.total_unregistered > 0:
    print(format_registration_report(report))
PYEOF
)

if [ -n "$RESULT" ]; then
  echo "" >&2
  echo "=== REGISTRATION CHECK WARNING ===" >&2
  echo "" >&2
  echo "$RESULT" >&2
  echo "" >&2
  echo "Run /register-component for fix instructions." >&2
  echo "=== END REGISTRATION CHECK ===" >&2
  echo "" >&2
fi

exit 0
