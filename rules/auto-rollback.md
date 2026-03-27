# Auto-Rollback Protocol

## Purpose

When the SDD verify-apply loop exhausts all retries (default: 3), automatically revert the failed changes to restore the codebase to a known-good state. This prevents broken code from accumulating when automated fixes fail.

## Trigger

Auto-rollback activates when:

1. `sdd-verify` returns FAIL with CRITICAL issues
2. The retry count reaches `max_retries` (default: 3)
3. The orchestrator reports: "Verify-apply loop exceeded 3 retries"

The `auto-rollback-trigger.sh` PostToolUse hook detects this pattern in agent output and initiates the rollback.

## Phase-Aware Behavior

| Phase | Behavior |
|-------|----------|
| `reconstruction` | Auto-execute rollback immediately |
| `stabilization` | Auto-execute rollback immediately |
| `production` | HALT — require human approval before rollback |
| `maintenance` | HALT — require human approval before rollback |

## Rollback Process

1. **Identify commits**: Read SDD DAG state to find commits from the failed `sdd-apply`
2. **Create rollback branch**: `git checkout -b rollback/{change-name}`
3. **Revert commits**: `git revert --no-edit HEAD~N..HEAD`
4. **Verify rollback**: Run build and lint to confirm the rollback is clean
5. **Update DAG state**: Record rollback in Engram with phase: `rollback`
6. **Report**: Output structured rollback report with status

## SDD DAG Integration

The rollback adds a new phase to the SDD dependency graph:

```
proposal -> specs --> tasks -> apply <-> verify -> archive
             ^                   ^         |
             |                   |         v
           design             (retry)   rollback (if retries exhausted)
```

DAG state after rollback:

```yaml
change: {change-name}
phase: rollback
retry_count: 3
max_retries: 3
rollback:
  branch: rollback/{change-name}
  commits_reverted: N
  build_status: PASS/FAIL
  timestamp: {ISO}
```

## Rollback Failure Handling

If the rollback itself fails (merge conflicts, build still broken):

1. Do NOT force-push or use destructive git operations
2. Escalate to human with full context
3. Include: conflicting files, attempted reverts, current branch state
4. Suggest manual resolution steps

## Safety Boundaries

Auto-rollback NEVER:
- Force-pushes to any branch
- Deletes branches
- Modifies the main/master branch directly
- Runs database migrations or rollbacks
- Changes environment variables or secrets

## Monitoring

Rollback events are logged to `.cognitive-os/metrics/auto-rollback.jsonl`:

```json
{
  "timestamp": "ISO-8601",
  "change": "change-name",
  "phase": "current-project-phase",
  "trigger": "verify-apply-exhaustion",
  "commits_reverted": 3,
  "build_status": "PASS",
  "outcome": "success"
}
```

## Hook Details

- **Trigger hook**: `hooks/auto-rollback-trigger.sh` (PostToolUse on Agent)
- **Skill**: `skills/auto-rollback/SKILL.md`
- **Engram topic**: `planning/{change-name}/state`

## Contextual Trigger

This rule is loaded when: rollback, revert, verify failure, retry exhaustion, sdd-verify fail.
