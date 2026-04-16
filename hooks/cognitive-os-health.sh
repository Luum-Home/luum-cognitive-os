#!/usr/bin/env bash
# Cognitive OS Health — SessionStart quick-check (1-line summary)
# Outputs: "Cognitive OS: X/Y OK | Phase: Z | Budget: $0/$N | Down: component1, component2"
set -euo pipefail

# Find docker binary (varies by OS/install)
DOCKER="$(command -v docker 2>/dev/null || echo "/Applications/Docker.app/Contents/Resources/bin/docker")"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
AOS="$PROJECT_DIR/.cognitive-os"

ok=0
warn=0
fail=0
total=0
failures=""

check() {
  local name="$1" status="$2"
  total=$((total + 1))
  case "$status" in
    OK)   ok=$((ok + 1)) ;;
    WARN) warn=$((warn + 1)) ;;
    FAIL) fail=$((fail + 1)); failures="${failures:+$failures, }$name" ;;
  esac
}

# 1. Hooks — extract .sh paths from JSON, check they exist and are executable
if [ -f "$PROJECT_DIR/.claude/settings.local.json" ]; then
  hook_files=$(python3 -c "
import json, re, sys
with open('$PROJECT_DIR/.claude/settings.local.json') as f:
    data = json.load(f)
hooks = data.get('hooks', {})
paths = set()
for event_hooks in hooks.values():
    if isinstance(event_hooks, list):
        for entry in event_hooks:
            for h in (entry.get('hooks', []) if isinstance(entry, dict) else []):
                cmd = h.get('command', '')
                for m in re.findall(r'[\"\\s]([^\"\\'\\s]*\\.sh)', cmd):
                    paths.add(m.replace('\$CLAUDE_PROJECT_DIR', '$PROJECT_DIR'))
for p in sorted(paths):
    print(p)
" 2>/dev/null || true)
  if [ -n "$hook_files" ]; then
    total_hooks=$(echo "$hook_files" | wc -l | tr -d ' ')
    exec_hooks=0
    while IFS= read -r f; do
      [ -x "$f" ] && exec_hooks=$((exec_hooks + 1))
    done <<< "$hook_files"
    [ "$exec_hooks" -eq "$total_hooks" ] && check "Hooks" "OK" || check "Hooks" "WARN"
  else
    check "Hooks" "WARN"
  fi
else
  check "Hooks" "FAIL"
fi

# 2. Rules
os_rules=$(find "$AOS/rules" -name '*.md' ! -name 'RULES-COMPACT.md' 2>/dev/null | wc -l | tr -d ' ')
proj_rules=$(find "$PROJECT_DIR/.claude/rules" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
[ -f "$AOS/rules/RULES-COMPACT.md" ] && check "Rules" "OK" || check "Rules" "WARN"

# 3. Skills
os_skills=$(find "$AOS/skills" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
[ -f "$AOS/skills/CATALOG.md" ] && check "Skills" "OK" || check "Skills" "WARN"

# 4. Squads
squad_count=$(find "$AOS/squads" -name '*.yaml' 2>/dev/null | wc -l | tr -d ' ')
[ "$squad_count" -gt 0 ] && check "Squads" "OK" || check "Squads" "WARN"

# 5. Agents
os_agents=$(find "$AOS/agents" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
global_agents=$(find "$HOME/.claude/agents" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
agent_total=$((os_agents + global_agents))
[ "$agent_total" -gt 0 ] && check "Agents" "OK" || check "Agents" "WARN"

# 6. Metrics
if [ -d "$AOS/metrics" ]; then
  metric_files=$(find "$AOS/metrics" -name '*.jsonl' 2>/dev/null | wc -l | tr -d ' ')
  with_data=0
  while IFS= read -r f; do
    [ -s "$f" ] && with_data=$((with_data + 1))
  done < <(find "$AOS/metrics" -name '*.jsonl' 2>/dev/null)
  [ "$with_data" -eq "$metric_files" ] && check "Metrics" "OK" || check "Metrics" "WARN"
else
  check "Metrics" "FAIL"
fi

# 7. Hook health — analyze heartbeats from hook-health.jsonl
hook_errors=0
stale_hooks=""
HEALTH_FILE="$AOS/metrics/hook-health.jsonl"
if [ -f "$HEALTH_FILE" ]; then
  cutoff_epoch=$(date -v-24H +%s 2>/dev/null || date -d '24 hours ago' +%s 2>/dev/null || echo 0)
  if command -v python3 >/dev/null 2>&1; then
    read -r hook_errors stale_hooks <<< "$(python3 -c "
import json, sys, os
from datetime import datetime, timedelta, timezone

cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
errors = 0
last_seen = {}  # hook -> latest timestamp

for line in open('$HEALTH_FILE'):
    line = line.strip()
    if not line:
        continue
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        continue
    ts_str = entry.get('timestamp', '')
    hook = entry.get('hook', '')
    exit_code = entry.get('exit_code', 0)
    try:
        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        continue
    if ts >= cutoff:
        if exit_code != 0:
            errors += 1
        if hook not in last_seen or ts > last_seen[hook]:
            last_seen[hook] = ts

# Stale = hooks that appear in the file but last heartbeat > 24h ago
all_hooks = set()
for line in open('$HEALTH_FILE'):
    line = line.strip()
    if not line:
        continue
    try:
        entry = json.loads(line)
        h = entry.get('hook', '')
        if h:
            all_hooks.add(h)
    except json.JSONDecodeError:
        continue

stale = sorted(h for h in all_hooks if h not in last_seen)
print(errors, ','.join(stale) if stale else '')
" 2>/dev/null || echo "0 ")"
  fi
  if [ "$hook_errors" -gt 0 ] || [ -n "$stale_hooks" ]; then
    check "HookHealth" "WARN"
  else
    check "HookHealth" "OK"
  fi
else
  # No heartbeat file yet — not an error, just no data
  check "HookHealth" "OK"
fi

# 8. Phase + Budget from cognitive-os.yaml
phase="unknown"
budget="?"
if [ -f "$AOS/cognitive-os.yaml" ]; then
  phase=$(grep -E '^\s+phase:' "$AOS/cognitive-os.yaml" | head -1 | sed 's/.*phase:[[:space:]]*//' | sed 's/[[:space:]]*#.*//')
  budget=$(grep 'monthly_limit_usd:' "$AOS/cognitive-os.yaml" | head -1 | sed 's/.*monthly_limit_usd:[[:space:]]*//' | tr -d ' ')
  check "Config" "OK"
else
  check "Config" "FAIL"
fi

# 9. Docker services (quick check, non-blocking)
for svc in langfuse-web litellm nemo-guardrails paperclip; do
  status=$($DOCKER compose -f "$PROJECT_DIR/docker-compose.cognitive-os.yml" ps --format '{{.State}}' "$svc" 2>/dev/null || true)
  if echo "$status" | grep -qi "running"; then
    check "$svc" "OK"
  else
    check "$svc" "FAIL"
  fi
done

# 10. Progressive loading
if [ -f "$AOS/skills/CATALOG.md" ] && [ -f "$AOS/rules/RULES-COMPACT.md" ]; then
  check "ProgLoad" "OK"
else
  check "ProgLoad" "WARN"
fi

# 11. Templates
tmpl_count=$(find "$AOS/templates" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
[ "$tmpl_count" -gt 0 ] && check "Templates" "OK" || check "Templates" "WARN"

# 12. Workflows
[ -f "$AOS/workflows/run.py" ] && check "Workflows" "OK" || check "Workflows" "WARN"

# 13. Repair system — check repair outcomes and circuit breakers
repair_summary=""
REPAIR_FILE="$AOS/metrics/repair-outcomes.jsonl"
CB_DIR="$AOS/metrics/circuit-breaker"
if [ -f "$REPAIR_FILE" ] || [ -d "$CB_DIR" ]; then
  repair_ok=0
  repair_fail=0
  open_breakers=0
  # Count repair outcomes from last 24h
  if [ -f "$REPAIR_FILE" ]; then
    cutoff_24h=$(date -v-24H +%s 2>/dev/null || date -d '24 hours ago' +%s 2>/dev/null || echo 0)
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      r_epoch=$(echo "$line" | jq -r '.timestamp_epoch // 0' 2>/dev/null)
      r_result=$(echo "$line" | jq -r '.result // "unknown"' 2>/dev/null)
      if [ "$r_epoch" -gt "$cutoff_24h" ] 2>/dev/null; then
        case "$r_result" in
          success|ok) repair_ok=$((repair_ok + 1)) ;;
          *) repair_fail=$((repair_fail + 1)) ;;
        esac
      fi
    done < "$REPAIR_FILE"
  fi
  # Count OPEN circuit breakers
  if [ -d "$CB_DIR" ]; then
    for cb_file in "$CB_DIR"/*.json; do
      [ -f "$cb_file" ] || continue
      cb_state=$(jq -r '.state // "CLOSED"' "$cb_file" 2>/dev/null)
      [ "$cb_state" = "OPEN" ] && open_breakers=$((open_breakers + 1))
    done
  fi
  repair_total=$((repair_ok + repair_fail))
  if [ "$open_breakers" -gt 0 ] || { [ "$repair_total" -gt 0 ] && [ "$repair_fail" -gt "$repair_ok" ]; }; then
    check "Repairs" "WARN"
    repair_summary="${open_breakers} OPEN breakers, ${repair_ok}/${repair_total} success"
  else
    check "Repairs" "OK"
    if [ "$repair_total" -gt 0 ]; then
      repair_summary="${repair_ok}/${repair_total} success"
    fi
  fi
else
  # No repair data yet — not an error
  check "Repairs" "OK"
fi

# Summary line
summary="Cognitive OS: ${ok}/${total} OK"
[ "$warn" -gt 0 ] && summary="$summary | ${warn} WARN"
[ "$fail" -gt 0 ] && summary="$summary | ${fail} FAIL"
summary="$summary | Phase: ${phase} | Budget: \$0/\$${budget}"
[ -n "$failures" ] && summary="$summary | Down: ${failures}"
[ "$hook_errors" -gt 0 ] && summary="$summary | HookErrors: ${hook_errors}"
[ -n "$stale_hooks" ] && summary="$summary | StaleHooks: ${stale_hooks}"
[ -n "$repair_summary" ] && summary="$summary | Repairs: ${repair_summary}"

echo "$summary"
