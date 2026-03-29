# /auto-rollback

> Automatically revert commits from a failed sdd-apply when verify exhausts all retries.

---
description: "Auto-rollback failed SDD apply commits when verify-apply loop exceeds max retries"
triggers: ["/auto-rollback", "Verify-apply loop exceeded 3 retries"]
audience: project
---

## Instructions

This skill activates when `sdd-verify` has failed 3 times (max retries exceeded) for a given change. It reverts the commits introduced by the last `sdd-apply` phase and verifies the rollback builds cleanly.

### Phase-Aware Behavior

| Phase | Behavior |
|-------|----------|
| `reconstruction` | Auto-execute rollback without approval |
| `stabilization` | Auto-execute rollback without approval |
| `production` | HALT — present rollback plan, wait for human approval |
| `maintenance` | HALT — present rollback plan, wait for human approval |

### Step 1: Identify Commits to Revert

1. Read the SDD DAG state from Engram: `planning/{change-name}/state`
2. Identify the number of commits from the last `sdd-apply` phase
3. If the DAG state includes commit hashes, use those directly
4. Otherwise, use `git log --oneline` to identify the apply commits (look for commit messages referencing the change name)
5. Store the count as `N` (number of commits to revert)

### Step 2: Create Rollback Branch

```bash
git checkout -b rollback/{change-name}
```

If the branch already exists, append a timestamp: `rollback/{change-name}-{YYYYMMDD-HHMMSS}`

### Step 3: Revert Commits

```bash
git revert --no-edit HEAD~N..HEAD
```

Where `N` is the number of commits identified in Step 1.

If the revert has conflicts:
1. Attempt to resolve automatically (prefer the pre-apply state)
2. If auto-resolution fails: STOP, report conflicts to human

### Step 4: Verify Rollback

Run the project's build/compile command:
- Go: `go build ./...`
- TypeScript: `yarn build` or `npm run build`
- Read from `cognitive-os.yaml` project configuration if available

Run lint:
- Go: `golangci-lint run ./...`
- TypeScript: `yarn lint` or `eslint`

### Step 5: Report

Output a structured report:

```
AUTO-ROLLBACK REPORT:
  Change: {change-name}
  Commits Reverted: N
  Rollback Branch: rollback/{change-name}
  Build Status: PASS/FAIL
  Lint Status: PASS/FAIL

  Reverted Commits:
    - {hash} {message}
    - {hash} {message}

  Recommendation: {next steps}
```

### Step 6: Update DAG State

Save updated state to Engram with `topic_key: "planning/{change-name}/state"`:

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

### Error Handling

If the rollback itself fails (revert conflicts, build still fails after revert):

1. Do NOT force-push or destructive operations
2. Report to human with full context:
   - What commits were attempted to revert
   - What conflicts occurred
   - Current branch state
   - Recommended manual steps

## Acceptance Criteria

1. Rollback branch exists: `git branch --list 'rollback/{change-name}*' | wc -l >= 1`
2. Commits were reverted: `git log --oneline rollback/{change-name} | head -N` shows revert commits
3. Build passes on rollback branch: build command exits 0
4. DAG state updated in Engram with phase: rollback
5. If rollback fails: human escalation message is output
