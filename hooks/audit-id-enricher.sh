#!/usr/bin/env bash
# SCOPE: both
# audit-id-enricher.sh — PostToolUse hook on Agent|Bash
# CONCERNS: audit, cross-cutting-id
#
# Enriches the latest JSONL metric entries with audit context
# (session_id, sprint_id, change_id, branch).
#
# Exit codes:
#   0 — always (never blocks)

set -uo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || echo "")

# Only process Agent and Bash tool uses
case "$TOOL_NAME" in
    Agent|Bash) ;;
    *) exit 0 ;;
esac

# Determine project dir
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$CLAUDE_PROJECT_DIR"
elif [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$COGNITIVE_OS_PROJECT_DIR"
else
    PROJECT_DIR="$(pwd)"
fi

SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"

# Enrich the last line of cost-events.jsonl with audit context
python3 -c "
import json, sys
sys.path.insert(0, '$PROJECT_DIR')
from lib.audit_id import get_current_audit_context, enrich_jsonl_entry

project_dir = '$PROJECT_DIR'
session_id = '$SESSION_ID'

ctx = get_current_audit_context(project_dir, session_id)

cost_file = project_dir + '/.cognitive-os/metrics/cost-events.jsonl'
try:
    with open(cost_file) as f:
        lines = f.readlines()
    if lines:
        last = json.loads(lines[-1])
        if 'session_id' not in last:
            enriched = enrich_jsonl_entry(last, ctx)
            lines[-1] = json.dumps(enriched) + '\n'
            with open(cost_file, 'w') as f:
                f.writelines(lines)
except FileNotFoundError:
    pass
except Exception:
    pass
" 2>/dev/null || true

exit 0
