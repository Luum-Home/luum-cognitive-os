---
type: quality-synthesis
source: docs/09-Quality/manual-tests/task-lifecycle-worktree-pr-flow.md
provenance: "Validates the ADR-162 task lifecycle protocol (statuses, question types, interruption reasons, worktree/PR vocabulary) as a contract/manual proof before the future cosd runtime enforces it."
---

## What it is
A contract-level manual test confirming that `manifests/task-lifecycle-schema.yaml` defines the full vocabulary ADR-162 specifies for task status, question, interruption, communication-event, worktree, and PR handling — proving the vocabulary is explicit and reviewable ahead of runtime enforcement by the future `cosd`.

## Key mechanics
- Task statuses must include `queued`, `running`, `waiting_for_human`, `interrupted`, `resumable`, `pr_ready`, `approved`, `merged`, and terminal states, each non-terminal status carrying an explicit `allowed_next` list.
- Question types: `requirement`, `approval`, `credential`, `conflict`, `product_decision`, `clarification`, `review`.
- Interruption reasons: `operator_interrupt`, `compaction`, `crash`, `auth_required`, `path_conflict`, `merge_conflict`, `policy_block`.
- Communication event types: `question.asked`, `question.answered`, `task.interrupted`, `task.resumed`, `pr.created`, `pr.merged`.
- Worktree path template `.worktrees/{task_id}`, branch template `codex/{task_id}-{slug}`; cleanup is blocked when tracked changes lack a patch bundle, a branch is unmerged/not abandoned, questions are unresolved, or evidence is missing.
- PR body must include Task, Scope, Claimed Paths, Evidence, Open Questions, Risks, and Rollback sections; direct push to main, force-push, merge without approval, and publishing secret-bearing logs are blocked actions.
- Automated checks: `tests/contracts/test_task_lifecycle_schema.py`, `tests/audit/test_adr_contracts.py` + `test_adr_locations.py`.

## Relations & where used
Companion to `remote-control-plane-boundary.md` (ADR-161) in the same research-first proof family covering future remote/`cosd` control-plane behavior; both are explicitly contract/manual proofs, not runtime enforcement proofs.

## Status / caveats
No dated evidence block embedded. The source file is visibly truncated — its final numbered checklist item ("The next implementation can target local queue/worktree allocation first,") cuts off mid-sentence with no closing clause; flagged as a source inconsistency, not completed here. Explicitly states no runtime support claim is made beyond the contract/manual proof.
