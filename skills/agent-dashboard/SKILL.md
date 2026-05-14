---
name: agent-dashboard
description: 'Use when you need this Cognitive OS skill: Show real-time status of
  all running background agents; do not use when a narrower skill directly matches
  the task.'
audience: os
scope: os
version: 1.0.0
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bagent[- ]?dashboard\b
  confidence: 0.95
- pattern: \b(agent\s+status|running\s+agents|background\s+agents)\b
  confidence: 0.8
- pattern: \bshow\s+agents?\b
  confidence: 0.75
summary_line: Show real-time status of all running background agents.
routing_intents:
- intent: agent_dashboard_request
  description: User asks to show real-time status of all running background agents.
  confidence: 0.85
triggers:
- agent-dashboard
- /agent-dashboard
- Show real-time status of all running background agents
---
<!-- SCOPE: both -->
# /agent-dashboard

Show status of all background agents launched in this session.

## Usage

When the user asks about agent status, progress, or says "/agent-dashboard":

```python
from lib.agent_output_monitor import AgentOutputMonitor
import os

# Auto-detect the tasks directory from the session
tasks_dir = os.environ.get("CLAUDE_TASKS_DIR", "/private/tmp/claude-501")

# Find the right session directory
for root, dirs, files in os.walk(tasks_dir):
    if "tasks" in dirs:
        tasks_dir = os.path.join(root, "tasks")
        break

m = AgentOutputMonitor(tasks_dir)
agents = [s for s in m.check_all() if s.agent_id.startswith('a') and s.tool_call_count > 0]
running = [s for s in agents if s.status in ('running', 'idle') and s.seconds_since_activity < 300]

for s in sorted(running, key=lambda x: x.seconds_since_activity):
    age = f'{int(s.seconds_since_activity)}s' if s.seconds_since_activity < 60 else f'{int(s.seconds_since_activity/60)}m'
    print(f'  {s.agent_id[:12]} [{s.status:7}] {s.tool_call_count:3} tools | {age} ago')
print(f'---')
print(f'{len(running)} active agents')
```

## Output Format

```
  ae13dfaf64a9 [running]  28 tools | 2s ago
  aba38f5f1edb [running]  37 tools | 3s ago
---
2 active agents
```

## Auto-polling

The orchestrator can set up a CronCreate every 2 minutes to auto-report. Use:
```
CronCreate(cron="*/2 * * * *", prompt="Run /agent-dashboard and report to user")
```
