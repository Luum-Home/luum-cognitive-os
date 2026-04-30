<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Dry-Run Preview Protocol

## Purpose

Allow users to preview what agents WOULD do without actually executing them. Essential for validating SDD pipelines, understanding task scope, and previewing changes before committing resources.

## Activation

Set the environment variable `DRY_RUN=true` before invoking any command:

```bash
DRY_RUN=true claude "run /sdd-ff my-feature"
```

Or within a session, set:
```
export DRY_RUN=true
```

To deactivate, unset the variable or set `DRY_RUN=false`.

## Behavior

When `DRY_RUN=true` is set:

1. The `dry-run-preview.sh` PreToolUse hook intercepts ALL Agent/task/delegate tool calls
2. Instead of executing, it outputs: `DRY-RUN: Would execute: {task description}`
3. The hook exits with code 2 (BLOCK), preventing the agent from launching
4. The interception is logged to `.cognitive-os/metrics/dry-run.jsonl`

## SDD Integration

Dry-run mode is particularly useful with SDD pipelines:

| Command | Dry-Run Behavior |
|---------|-----------------|
| `DRY_RUN=true /sdd-ff my-feature` | Shows all phases (propose, spec, design, tasks) without executing |
| `DRY_RUN=true /sdd-apply my-feature` | Shows what the apply phase would do without writing code |
| `DRY_RUN=true /sdd-verify my-feature` | Shows what verification would check without running |

## What Gets Logged

Each dry-run interception creates an entry in `.cognitive-os/metrics/dry-run.jsonl`:

```json
{
  "timestamp": "ISO-8601",
  "tool": "Agent|task|delegate",
  "task_description": "first 500 chars of the task prompt",
  "action": "blocked"
}
```

## Use Cases

1. **Pipeline preview**: See all SDD phases before committing time and budget
2. **Cost estimation**: Count how many agent calls a task would make
3. **Scope validation**: Verify the orchestrator is delegating correctly
4. **Training**: Learn what the system does without side effects
5. **CI/CD integration**: Validate pipeline configurations without execution

## Limitations

- Dry-run only blocks Agent/task/delegate tool calls
- Direct Bash, Read, Edit, Write tool calls are NOT blocked
- The orchestrator itself may still perform coordination logic
- Sub-agent prompts are shown but not executed, so downstream phases won't generate

## Hook Details

- **Hook**: `hooks/dry-run-preview.sh`
- **Type**: PreToolUse
- **Matcher**: Agent
- **Exit code**: 2 (BLOCK) when DRY_RUN=true, 0 otherwise
- **Performance**: < 100ms (reads env var, formats output)
