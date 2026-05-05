# Manual Test — Task Lifecycle, Questions, Interruptions, Worktrees, and PRs

## Purpose

Validate the protocol defined by ADR-162 before the full `cosd` runtime enforces
it. The test is contract/manual today: it proves the vocabulary and expected
flow are explicit, reviewable, and compatible with future remote ingress.

## Preconditions

- Worktree is clean or the operator knows which uncommitted files belong to
  another task.
- No provider credentials are required.
- No real PR needs to be opened for this contract-only slice.

## Checklist

1. Open `manifests/task-lifecycle-schema.yaml`.
2. Confirm task statuses include `queued`, `running`, `waiting_for_human`,
   `interrupted`, `resumable`, `pr_ready`, `approved`, `merged`, and terminal
   states.
3. Confirm every non-terminal status has an explicit `allowed_next` list.
4. Confirm question types include `requirement`, `approval`, `credential`,
   `conflict`, `product_decision`, `clarification`, and `review`.
5. Confirm interruption reasons include `operator_interrupt`, `compaction`,
   `crash`, `auth_required`, `path_conflict`, `merge_conflict`, and
   `policy_block`.
6. Confirm communication event types include `question.asked`,
   `question.answered`, `task.interrupted`, `task.resumed`, `pr.created`, and
   `pr.merged`.
7. Confirm worktree path template is `.worktrees/{task_id}` and branch template
   is `codex/{task_id}-{slug}`.
8. Confirm worktree cleanup is blocked when tracked changes lack a patch bundle,
   a branch is not merged/abandoned, questions are unresolved, or evidence is
   missing.
9. Confirm PR body sections include Task, Scope, Claimed Paths, Evidence, Open
   Questions, Risks, and Rollback.
10. Confirm direct push to main, force-push, merge without approval, and
    publishing secret-bearing logs are blocked actions.

## Automated checks

```bash
python3 -m pytest tests/contracts/test_task_lifecycle_schema.py -q
python3 -m pytest tests/audit/test_adr_contracts.py tests/audit/test_adr_locations.py -q
```

## Expected result

- The contract test passes.
- ADR audit/location tests pass.
- No runtime support claim is made beyond the contract/manual proof.
- The next implementation can target local queue/worktree allocation first,
  without Telegram, Paperclip, GitHub, or provider credentials.
