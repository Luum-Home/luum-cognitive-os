#!/usr/bin/env bash
# SessionStart hook: quick component health check
# Only runs every 24h (checks last run timestamp)

METRICS_DIR=".cognitive-os/metrics"
LAST_RUN_FILE="$METRICS_DIR/usage-health-last-run"

# Skip if ran within last 24h
if [ -f "$LAST_RUN_FILE" ]; then
    last_run=$(cat "$LAST_RUN_FILE" 2>/dev/null || echo "0")
    now=$(date +%s)
    diff=$((now - last_run))
    if [ "$diff" -lt 86400 ]; then
        exit 0  # Skip — ran recently
    fi
fi

# Run the health check
python3 -c "
from lib.component_usage_tracker import ComponentUsageTracker
t = ComponentUsageTracker()
r = t.generate_usage_report()
health = r.get('dead_weight', {}).get('health_pct', 0)
if health < 60:
    import sys
    print(f'COMPONENT HEALTH WARNING: {health:.0f}% — run /usage-report for details', file=sys.stderr)
" 2>&1 || true

# Update last run timestamp
mkdir -p "$METRICS_DIR" 2>/dev/null
date +%s > "$LAST_RUN_FILE" 2>/dev/null

exit 0
