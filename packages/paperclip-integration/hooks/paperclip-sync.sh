#!/usr/bin/env bash
# paperclip-sync.sh — Sync Cognitive OS metrics to Paperclip dashboard
# Trigger: Stop (before session-cleanup.sh)
#
# Pushes session summary, cost totals, active tasks, and agent completion
# statuses to Paperclip on session end.

_HOOK_NAME="paperclip-sync"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PAPERCLIP_URL="${COGNITIVE_OS_PAPERCLIP_URL:-http://localhost:3200}"
METRICS_DIR="$(_resolve_metrics_dir)"

# Check if Paperclip is available
if ! curl -s --connect-timeout 2 "$PAPERCLIP_URL/api/health" >/dev/null 2>&1; then
  exit 0  # Paperclip not running, skip silently
fi

# Try the structured Python client first, fall back to basic curl
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-unknown}"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Gather session metrics
ERRORS=$(wc -l < "$METRICS_DIR/error-learning.jsonl" 2>/dev/null | tr -d ' ' || echo 0)
REPAIRS_OK=$(grep -c '"success"' "$METRICS_DIR/repair-outcomes.jsonl" 2>/dev/null || echo 0)
REPAIRS_FAIL=$(grep -c '"failure"' "$METRICS_DIR/repair-outcomes.jsonl" 2>/dev/null || echo 0)
SKILLS=$(wc -l < "$METRICS_DIR/skill-metrics.jsonl" 2>/dev/null | tr -d ' ' || echo 0)
REGISTRY_SIZE=$(wc -l < "$PROJECT_DIR/.cognitive-os/metrics/remediation-registry.jsonl" 2>/dev/null | tr -d ' ' || echo 0)

# Gather error learning stats by type
ERROR_STATS="{}"
if [[ -f "$METRICS_DIR/error-learning.jsonl" && -s "$METRICS_DIR/error-learning.jsonl" ]]; then
  ERROR_STATS=$(jq -s '
    {
      total_errors: length,
      errors_by_type: (group_by(.type) | map({key: .[0].type, value: length}) | from_entries),
      errors_by_service: (group_by(.service) | map({key: (.[0].service // "unknown"), value: length}) | from_entries),
      auto_repairs: {
        succeeded: '"$REPAIRS_OK"',
        failed: '"$REPAIRS_FAIL"'
      }
    }
  ' "$METRICS_DIR/error-learning.jsonl" 2>/dev/null || echo '{}')
fi

# Gather cost events (last 50)
COST_EVENTS="[]"
if [[ -f "$METRICS_DIR/cost-events.jsonl" && -s "$METRICS_DIR/cost-events.jsonl" ]]; then
  COST_EVENTS=$(tail -50 "$METRICS_DIR/cost-events.jsonl" | jq -s '.' 2>/dev/null || echo '[]')
fi

# Gather skill metrics summary
SKILL_SUMMARY="{}"
if [[ -f "$METRICS_DIR/skill-metrics.jsonl" && -s "$METRICS_DIR/skill-metrics.jsonl" ]]; then
  SKILL_SUMMARY=$(jq -s '
    {
      total_invocations: length,
      success_count: [.[] | select(.success == true)] | length,
      failure_count: [.[] | select(.success == false)] | length,
      by_skill: (group_by(.skill) | map({
        key: .[0].skill,
        value: {count: length, successes: ([.[] | select(.success == true)] | length)}
      }) | from_entries)
    }
  ' "$METRICS_DIR/skill-metrics.jsonl" 2>/dev/null || echo '{}')
fi

# Gather KPI snapshot if available
KPI_DATA="{}"
if [[ -f "$METRICS_DIR/kpi-history.jsonl" && -s "$METRICS_DIR/kpi-history.jsonl" ]]; then
  KPI_DATA=$(tail -1 "$METRICS_DIR/kpi-history.jsonl" 2>/dev/null || echo '{}')
fi

# Gather session cost total for spend tracking
SESSION_COST_USD=0
SESSION_TOKENS=0
SESSION_MODEL="mixed"
if [[ -f "$METRICS_DIR/cost-events.jsonl" && -s "$METRICS_DIR/cost-events.jsonl" ]]; then
  SESSION_COST_USD=$(jq -s '[.[].estimated_cost_usd // 0] | add // 0' "$METRICS_DIR/cost-events.jsonl" 2>/dev/null || echo 0)
  SESSION_TOKENS=$(jq -s '[.[] | ((.input_tokens // 0) + (.output_tokens // 0))] | add // 0' "$METRICS_DIR/cost-events.jsonl" 2>/dev/null || echo 0)
  # Dominant model = model with most entries
  SESSION_MODEL=$(jq -s '[.[].model] | group_by(.) | sort_by(-length) | .[0][0] // "unknown"' "$METRICS_DIR/cost-events.jsonl" 2>/dev/null || echo "unknown")
fi

# Gather active tasks for issue sync
ACTIVE_TASKS="[]"
TASKS_FILE="$PROJECT_DIR/.claude/tasks/active-tasks.json"
if [[ -f "$TASKS_FILE" && -s "$TASKS_FILE" ]]; then
  ACTIVE_TASKS=$(jq '.tasks // []' "$TASKS_FILE" 2>/dev/null || echo '[]')
fi

# Try Python client for structured push
PYTHON_PUSH_OK=false
if command -v python3 >/dev/null 2>&1; then
  python3 -c "
import sys, json, os
sys.path.insert(0, '$PROJECT_DIR/lib')
os.environ['COGNITIVE_OS_PAPERCLIP_URL'] = '$PAPERCLIP_URL'
try:
    from paperclip_client import PaperclipClient
    client = PaperclipClient()
    if not client.is_available():
        print('UNAVAILABLE')
        sys.exit(0)

    # 1. Push session summary (backward compatible)
    summary = {
        'session_id': '$SESSION_ID',
        'timestamp': '$TIMESTAMP',
        'metrics': {
            'errors_captured': $ERRORS,
            'repairs_succeeded': $REPAIRS_OK,
            'repairs_failed': $REPAIRS_FAIL,
            'skills_executed': $SKILLS,
            'registry_size': $REGISTRY_SIZE,
        },
        'error_stats': json.loads('''$ERROR_STATS'''),
        'skill_summary': json.loads('''$SKILL_SUMMARY'''),
        'kpi_snapshot': json.loads('''$KPI_DATA'''),
        'cost_events': json.loads('''$COST_EVENTS'''),
    }
    client.push_session_summary(summary)

    # 2. Push session cost to spend tracker
    cost = float($SESSION_COST_USD)
    tokens = int($SESSION_TOKENS)
    model = $SESSION_MODEL if isinstance($SESSION_MODEL, str) else 'unknown'
    if cost > 0:
        client.push_spend(cost, model, tokens)

    # 3. Push active tasks as notifications (completed tasks)
    tasks = json.loads('''$ACTIVE_TASKS''')
    completed = [t for t in tasks if t.get('status') == 'completed']
    for task in completed[:10]:  # Cap at 10 to avoid flooding
        desc = task.get('description', task.get('id', 'unknown'))
        client.push_notification(
            'Task completed: %s' % desc[:80],
            'Session: $SESSION_ID',
            'info'
        )

    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
" 2>/dev/null | grep -q 'OK' && PYTHON_PUSH_OK=true
fi

# Fall back to basic curl if Python client failed
if [[ "$PYTHON_PUSH_OK" != "true" ]]; then
  PAYLOAD=$(jq -cn \
    --arg sid "$SESSION_ID" \
    --arg ts "$TIMESTAMP" \
    --argjson errors "$ERRORS" \
    --argjson repairs_ok "$REPAIRS_OK" \
    --argjson repairs_fail "$REPAIRS_FAIL" \
    --argjson skills "$SKILLS" \
    --argjson registry "$REGISTRY_SIZE" \
    '{
      type: "cognitive-os-session",
      session_id: $sid,
      timestamp: $ts,
      metrics: {
        errors_captured: $errors,
        repairs_succeeded: $repairs_ok,
        repairs_failed: $repairs_fail,
        skills_executed: $skills,
        registry_size: $registry
      }
    }')

  # Push to Paperclip (fire and forget)
  curl -s -X POST "$PAPERCLIP_URL/api/artifacts" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    --connect-timeout 2 \
    --max-time 5 \
    >/dev/null 2>&1 || true
fi

exit 0
