# Testing Agent Teams with Cognitive OS Hooks

Agent Teams is a Claude Code experimental feature that enables multi-agent collaboration
within a single session. Three COS hooks integrate with the Agent Teams lifecycle:
`TeammateIdle`, `TaskCreated`, and `TaskCompleted`.

Agent Teams requires an **interactive Claude Code session** -- it cannot be tested via
subprocess or CI. This document covers both automated hook validation and manual
end-to-end testing.

## Prerequisites

- Claude Code v2.1.32+ (with Agent Teams support)
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` set in environment or settings
- All 3 hooks registered in `.claude/settings.json` (see Hook Registration below)
- `jq` installed (used by all hooks for JSON parsing)

## Hook Registration

The following events must be registered in `.claude/settings.json`:

| Event | Hook Script | Purpose |
|-------|-------------|---------|
| `TeammateIdle` | `hooks/teammate-idle.sh` | Checks for unclaimed tasks when a teammate is about to go idle |
| `TaskCreated` | `hooks/task-created.sh` | Validates task quality (description length, acceptance criteria) |
| `TaskCompleted` | `hooks/task-completed.sh` | Validates completion output, updates active-tasks.json |

Verify registration:

```bash
python3 -c "
import json
s = json.load(open('.claude/settings.json'))
for event in ['TeammateIdle', 'TaskCreated', 'TaskCompleted']:
    if event in s.get('hooks', {}):
        print(f'{event}: registered')
    else:
        print(f'{event}: MISSING')
"
```

## Automated Hook Validation

Run the automated test suite to verify hooks parse JSON correctly, handle edge cases,
and enforce phase-aware behavior:

```bash
python3 -m pytest tests/hooks/test_agent_teams_hooks.py -v
```

This validates 28 scenarios:
- Settings registration (4 tests)
- TeammateIdle: valid JSON, pending tasks, empty/malformed stdin, private mode, metrics (7 tests)
- TaskCreated: valid tasks, short descriptions, production phase, empty/malformed stdin (8 tests)
- TaskCompleted: valid output, short output, trust reports, task updates, empty/malformed stdin (9 tests)

### Mock Input Testing (manual)

Test hooks with simulated JSON on stdin:

```bash
# TeammateIdle -- should exit 0 (no tasks file)
echo '{"hook_event_name": "TeammateIdle", "agent_id": "test-1"}' \
  | bash hooks/teammate-idle.sh
echo "Exit: $?"

# TaskCreated -- should exit 0 (valid description)
echo '{"hook_event_name": "TaskCreated", "description": "Implement auth endpoint with JWT validation"}' \
  | bash hooks/task-created.sh
echo "Exit: $?"

# TaskCreated -- should exit 2 (too short)
echo '{"hook_event_name": "TaskCreated", "description": "fix"}' \
  | bash hooks/task-created.sh
echo "Exit: $?"

# TaskCompleted -- should exit 0 (substantive output)
echo '{"hook_event_name": "TaskCompleted", "output": "Implemented the endpoint. All 12 tests pass. Coverage at 85%."}' \
  | bash hooks/task-completed.sh
echo "Exit: $?"

# TaskCompleted -- should exit 2 (output too short)
echo '{"hook_event_name": "TaskCompleted", "output": "done"}' \
  | bash hooks/task-completed.sh
echo "Exit: $?"
```

## Manual End-to-End Test Procedure

### Step 1: Start Claude Code with Agent Teams

```bash
cd /path/to/luum-agent-os
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude
```

### Step 2: Create a Team

Give Claude a task that naturally decomposes into parallel work:

> "Create a team of 3 to implement a REST health endpoint:
> one teammate for the handler, one for the tests, one for the docs.
> Each task must include acceptance criteria."

### Step 3: Observe Hook Behavior

Watch for these signals in the session output:

| Hook | What to Look For |
|------|-----------------|
| **TaskCreated** | Tasks with short descriptions are blocked (exit 2). Tasks in production phase without acceptance criteria are blocked. |
| **TeammateIdle** | When a teammate finishes and pending tasks remain, the hook suggests the next task (exit 2 keeps teammate active). |
| **TaskCompleted** | Completions with trivially short output are rejected (exit 2). In production phase, completions without a Trust Report are rejected. |

### Step 4: Verify Metrics

After the team completes:

```bash
# Check for metrics files
ls -la .cognitive-os/metrics/teammate-idle.jsonl \
       .cognitive-os/metrics/task-created.jsonl \
       .cognitive-os/metrics/task-completed.jsonl 2>/dev/null

# Or in the session-scoped directory
ls -la .cognitive-os/sessions/*/metrics/teammate-idle.jsonl \
       .cognitive-os/sessions/*/metrics/task-created.jsonl \
       .cognitive-os/sessions/*/metrics/task-completed.jsonl 2>/dev/null

# View recent events
tail -5 .cognitive-os/metrics/task-created.jsonl 2>/dev/null | jq .
tail -5 .cognitive-os/metrics/task-completed.jsonl 2>/dev/null | jq .
```

### Step 5: Verify active-tasks.json Updates

If tasks were registered in `.claude/tasks/active-tasks.json`, the `TaskCompleted`
hook should have marked completed tasks:

```bash
jq '.tasks[] | {id, status, completedAt}' .claude/tasks/active-tasks.json 2>/dev/null
```

## Phase-Aware Behavior

The hooks enforce stricter rules in production/maintenance phases:

| Phase | TaskCreated | TaskCompleted |
|-------|-------------|---------------|
| reconstruction | Blocks short descriptions only | Blocks short output only |
| stabilization | Blocks short descriptions only | Blocks short output only |
| production | Blocks short descriptions AND missing acceptance criteria | Blocks short output AND missing Trust Report |
| maintenance | Same as production | Same as production |

Change the phase in `cognitive-os.yaml` to test different behaviors:

```yaml
project:
  phase: production  # or: reconstruction, stabilization, maintenance
```

## Graceful Degradation

All hooks follow the COS graceful degradation pattern:
- Empty stdin: exit 0 (allow)
- Malformed JSON: exit 0 (allow)
- Missing expected fields: exit 0 (allow)
- Private mode active: exit 0 (skip all checks)
- Missing active-tasks.json: exit 0 (allow)

## Known Limitations

1. **Agent Teams is experimental** -- the stdin JSON format may change between Claude Code versions.
   The hooks extract fields defensively with multiple fallback paths.

2. **Cannot test event dispatch in CI** -- Agent Teams events are dispatched by the Claude Code
   runtime during interactive sessions. The automated tests validate hook behavior with mock input,
   not the full dispatch pipeline.

3. **SubagentStart hook not yet integrated** -- When Agent Teams matures, a `SubagentStart` hook
   could inject the COS agent preamble into each teammate's context automatically.

## Troubleshooting

**Hooks not firing**: Verify registration with the check script above. Restart Claude Code
after modifying `settings.json`.

**Exit code 5 on malformed JSON**: Fixed in the current version. The `|| true` guards on jq
pipelines prevent `set -euo pipefail` from killing the script on parse errors.

**Metrics not appearing**: Check that `.cognitive-os/metrics/` directory exists and is writable.
The hooks create it via `resolve_session_dir` if missing.
