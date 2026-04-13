#!/usr/bin/env bash
# SCOPE: both
# PostToolUse hook: Suppress metrics and error writing when private mode is active
# Runs BEFORE skill-metrics-tracker.sh and error-learning.sh
# Must complete in <1 second

set -euo pipefail

FLAG="/tmp/claude-private-mode-active"

# If private mode is NOT active, allow everything (pass through)
if [ ! -f "$FLAG" ]; then
  exit 0
fi

# Private mode IS active — consume stdin and exit silently
# This prevents downstream hooks from receiving data
cat > /dev/null
exit 0
