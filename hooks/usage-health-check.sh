#!/usr/bin/env bash
# SCOPE: os-only
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
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

# Run the lightweight startup check.
# The full usage report is intentionally too heavy for a SessionStart hook.
timeout 10 python3 -c "
from lib.component_usage_tracker import ComponentUsageTracker
t = ComponentUsageTracker('.')
r = t.generate_quick_health_report()
health = r.get('dead_weight', {}).get('health_pct', 100)
if health < 60:
    import sys
    print(f'COMPONENT HEALTH WARNING: {health:.0f}% — run /usage-report for details', file=sys.stderr)
" 2>&1 || true

# Update last run timestamp
mkdir -p "$METRICS_DIR" 2>/dev/null
date +%s > "$LAST_RUN_FILE" 2>/dev/null

exit 0
