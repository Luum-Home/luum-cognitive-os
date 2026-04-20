#!/usr/bin/env bash
# SessionStart: weekly ecosystem re-evaluation
# Checks plugin submodules for new commits and evaluated tools for staleness.
# Runs at most once every 7 days. Graceful — never blocks session start.
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
LAST_RUN="$METRICS_DIR/ecosystem-eval-last-run"

# ── 1. Check cadence — skip if ran within last 7 days ─────────────────────
mkdir -p "$METRICS_DIR"

if [ -f "$LAST_RUN" ]; then
    last=$(cat "$LAST_RUN" 2>/dev/null || echo "0")
    now=$(date +%s)
    age=$((now - last))
    if [ "$age" -lt 604800 ]; then
        exit 0
    fi
fi

# ── 2. Run evaluation ─────────────────────────────────────────────────────
timeout 30 python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from lib.ecosystem_evaluator import EcosystemEvaluator

e = EcosystemEvaluator('$PROJECT_DIR')
r = e.generate_evaluation_report()

plugins_with_updates = [p for p in r.get('plugins', []) if p.get('new_commits', 0) > 0]
stale_tools = [t for t in r.get('tools', []) if t.get('is_stale')]
reinvention = r.get('reinvention', [])

has_output = plugins_with_updates or stale_tools or reinvention
if has_output:
    report = e.format_report(r)
    print(report[:2000], file=sys.stderr)

e.save_check_timestamp()
" 2>&1 || true

exit 0
