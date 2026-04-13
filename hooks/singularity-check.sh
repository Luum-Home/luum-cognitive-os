#!/usr/bin/env bash
# SCOPE: both
# SessionStart hook: Quick singularity status check
# OFF by default. Set SINGULARITY_CHECK=true to enable.
# Reports pending events from the singularity controller.

set -euo pipefail

# Check if enabled (OFF by default)
SINGULARITY_CHECK="${SINGULARITY_CHECK:-false}"
if [ "$SINGULARITY_CHECK" != "true" ]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
SINGULARITY_SCRIPT="$PROJECT_DIR/lib/singularity.py"

# Require Python
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    PYTHON="$cmd"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  exit 0
fi

# Require singularity module
if [ ! -f "$SINGULARITY_SCRIPT" ]; then
  exit 0
fi

# Run a quick status check via Python
STATUS_OUTPUT=$($PYTHON -c "
import sys, os, json

sys.path.insert(0, '$PROJECT_DIR')

try:
    from lib.singularity import SingularityController
    controller = SingularityController('$PROJECT_DIR')
    events = controller.detect_events()

    if not events:
        print('No pending events')
        sys.exit(0)

    # Classify events
    counts = {}
    for ev in events:
        ev_type = ev.get('type', 'unknown')
        counts[ev_type] = counts.get(ev_type, 0) + 1

    parts = []
    for t, c in sorted(counts.items()):
        label = t.replace('_', ' ')
        parts.append(f'{c} {label}')

    total = sum(counts.values())
    detail = ', '.join(parts)
    print(f'{total} pending events ({detail})')
except Exception as e:
    print(f'Singularity check failed: {e}')
    sys.exit(0)
" 2>/dev/null) || true

if [ -n "$STATUS_OUTPUT" ]; then
  echo "Singularity: $STATUS_OUTPUT" >&2
fi

exit 0
