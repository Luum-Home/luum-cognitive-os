#!/usr/bin/env bash
# Stop hook: Record completed task info to task-history.jsonl
# Reads session cost from cost-events.jsonl, task info from active-tasks.json,
# computes models used/tokens/duration, appends to task-history.jsonl.
# Only records if meaningful work was done (cost > $0.01).

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
COST_FILE="$METRICS_DIR/cost-events.jsonl"
HISTORY_FILE="$METRICS_DIR/task-history.jsonl"
TASKS_FILE="$PROJECT_DIR/.claude/tasks/active-tasks.json"

# Exit early if no cost events
if [ ! -f "$COST_FILE" ]; then
  exit 0
fi

# Calculate total cost from cost events
TOTAL_COST=$(python3 -c "
import json, sys
total = 0.0
try:
    with open('$COST_FILE') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    ev = json.loads(line)
                    total += float(ev.get('estimated_cost_usd', 0))
                except (json.JSONDecodeError, ValueError):
                    pass
except OSError:
    pass
print(f'{total:.6f}')
" 2>/dev/null || echo "0.0")

# Only record if meaningful work was done
if python3 -c "import sys; sys.exit(0 if float('$TOTAL_COST') > 0.01 else 1)" 2>/dev/null; then
  :
else
  exit 0
fi

# Gather task info and record
python3 - "$COST_FILE" "$HISTORY_FILE" "$TASKS_FILE" <<'PYTHON_SCRIPT'
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

cost_file = sys.argv[1]
history_file = sys.argv[2]
tasks_file = sys.argv[3]

# Read cost events
events = []
try:
    with open(cost_file) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
except OSError:
    pass

if not events:
    sys.exit(0)

# Compute aggregates
total_cost = sum(float(ev.get("estimated_cost_usd", 0)) for ev in events)
total_in = sum(int(ev.get("input_tokens", 0)) for ev in events)
total_out = sum(int(ev.get("output_tokens", 0)) for ev in events)

# Models used
models_used = {}
for ev in events:
    model = ev.get("model", "unknown")
    models_used[model] = models_used.get(model, 0) + 1

# Duration from first to last event
timestamps = []
for ev in events:
    ts = ev.get("timestamp", "")
    if ts:
        try:
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            timestamps.append(parsed)
        except (ValueError, TypeError):
            pass

duration_minutes = 0.0
if len(timestamps) >= 2:
    timestamps.sort()
    delta = (timestamps[-1] - timestamps[0]).total_seconds()
    duration_minutes = delta / 60.0

# Extract task description from active-tasks.json
description = "session work"
task_type = "feature"
phases_executed = []
files_changed = 0

try:
    if os.path.exists(tasks_file):
        with open(tasks_file) as f:
            tasks_data = json.load(f)
        tasks = tasks_data.get("tasks", [])
        completed = [t for t in tasks if t.get("status") == "completed"]
        if completed:
            description = completed[-1].get("description", description)
            task_type = completed[-1].get("type", task_type)
except (OSError, json.JSONDecodeError, KeyError):
    pass

# Detect phases from agent names in cost events
phase_keywords = ["explore", "propose", "spec", "design", "tasks", "apply", "verify", "archive"]
for ev in events:
    agent = ev.get("agent", "").lower()
    for phase in phase_keywords:
        if phase in agent and phase not in phases_executed:
            phases_executed.append(phase)

# Build history entry
entry = {
    "description": description,
    "task_type": task_type,
    "phases_executed": phases_executed,
    "total_cost_usd": round(total_cost, 6),
    "tokens_in": total_in,
    "tokens_out": total_out,
    "models_used": models_used,
    "duration_minutes": round(duration_minutes, 2),
    "files_changed": files_changed,
    "timestamp": datetime.now(timezone.utc).isoformat(),
}

# Append to history
Path(history_file).parent.mkdir(parents=True, exist_ok=True)
try:
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
except OSError:
    pass

PYTHON_SCRIPT

exit 0
