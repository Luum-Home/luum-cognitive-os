#!/usr/bin/env bash
# SCOPE: os-only
# @weekly: run Sunday 02:00 via cron or /schedule; deferred until cron job is registered
# weekly-aspirational-audit.sh — ws8 weekly cron runner
#
# Runs aspirational_audit.py (which now auto-calls cos_classify_coverage.py)
# and writes outputs to standard locations.
#
# Recommended cron (run Sunday at 02:00 local time):
#   0 2 * * 0  cd /path/to/luum-agent-os && bash scripts/weekly-aspirational-audit.sh
#
# Or via CronCreate (in a Claude Code session):
#   /schedule "Run weekly aspirational audit" --cron "0 2 * * 0" \
#     --command "python3 scripts/aspirational_audit.py"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

echo "[weekly-aspirational-audit] $(date -u +%Y-%m-%dT%H:%M:%SZ) — starting"

python3 "$SCRIPT_DIR/aspirational_audit.py" "$@"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[weekly-aspirational-audit] completed successfully"
else
    echo "[weekly-aspirational-audit] completed with exit code $EXIT_CODE" >&2
fi

exit $EXIT_CODE
