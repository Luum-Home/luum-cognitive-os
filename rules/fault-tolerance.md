<!-- TIER: 2 -->
<!-- SCOPE: both -->
# Fault Tolerance Protocol

## 4-Tier Resilience Model

Inspired by OpenClaw's resilience architecture, adapted for Cognitive OS.

### Tier 1: Connection Resilience
- Automatic reconnection with exponential backoff
- Heartbeat monitoring
- Graceful shutdown with 250ms grace period

### Tier 2: LLM Call Resilience
- Auth profile rotation on credential errors
- Rate limit detection with gradual delay
- Model fallback chain (opus -> sonnet -> haiku)
- Thinking level reduction (extended -> normal -> low)
- Max retry: 24 base + 8 per profile, cap 160

### Tier 3: Context Resilience
- Pre-compaction flush (save to Engram before compaction via pre-compaction-flush.sh hook)
- Context overflow -> summarize + preserve last N turns
- Compaction diagnosis ID for post-mortem
- Session summary saved to Engram on every compaction

### Tier 4: Agent Resilience
- Subagent orphan detection (timeout-based)
- Parent notification on child failure
- Active tasks JSON for session recovery
- Idempotent re-launch via checkCommand

---

## Task Registration

### Before launching sub-agents
1. Register each task in `.claude/tasks/active-tasks.json` via the agent-prelaunch hook
2. Include `expectedOutputs` (key files the agent should create)
3. Include `checkCommand` (how to verify the task completed)

### After sub-agents complete
1. The agent-checkpoint hook auto-updates task status
2. Completed tasks are timestamped

### On session start
1. The session-resume hook auto-checks `.claude/tasks/active-tasks.json` for in_progress tasks
2. Tasks with verified outputs are auto-marked as completed
3. Tasks with missing outputs trigger a warning with recommended re-launch
4. The /resume-tasks skill is available as a manual fallback

## Idempotent agents
Every agent MUST check if its work already exists before starting:
- Check if target files exist
- Check if target Docker services are running
- If work is already done, report success without re-doing

## Task lifecycle
```
pending -> in_progress -> completed
                       -> failed -> (re-launch) -> in_progress
```

### Task Claiming

When multiple agents could work on the same task, agents MUST claim tasks before starting:

1. **Claim**: Set `claimed_by: {agent_id}` and `claimed_at: {ISO timestamp}` in the task entry
2. **Check before claim**: If `claimed_by` is already set AND the claiming agent is alive (PID check), skip the task
3. **Release on completion**: Clear `claimed_by` when task completes or fails
4. **Auto-release on timeout**: Claims expire after `claim_timeout_seconds` (default: 300)

This prevents duplicate work when the orchestrator launches multiple agents or when concurrent sessions work on the same project.

## Enriching task metadata

When the orchestrator launches a sub-agent for a task that produces known outputs, it should update the task entry in active-tasks.json BEFORE launch by writing directly:

```bash
jq --arg id "$TASK_ID" \
   --argjson outputs '["path/to/expected/file.ts"]' \
   --arg cmd "test -f path/to/expected/file.ts" \
   '(.tasks[] | select(.id == $id)) |= . + {expectedOutputs: $outputs, checkCommand: $cmd}' \
   .claude/tasks/active-tasks.json > /tmp/tasks.tmp && mv /tmp/tasks.tmp .claude/tasks/active-tasks.json
```

This enables the /resume-tasks skill and session-resume hook to verify completion without re-running the agent.

## Cleanup policy
- Completed tasks older than 7 days are pruned by /resume-tasks
- Failed tasks are kept indefinitely until explicitly resolved
- The active-tasks.json file is session state (gitignored), not source code
