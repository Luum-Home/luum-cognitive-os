# Merge Readiness: Master Plan Portability

> Snapshot for deciding when `codex/master-plan-portability` is ready to merge into `main` and when local/remote branches can be deleted.

## Branch State

Current branch:

- `codex/master-plan-portability`

Observed comparison after fetching remotes, before committing this report:

- `codex/master-plan-portability` is at least 4 commits ahead of `origin/codex/master-plan-portability`.
- `codex/master-plan-portability` is 32 commits ahead of local `main`.
- `codex/master-plan-portability` is 58 commits ahead of `origin/main`.
- local `main` is ahead of `origin/main`, so the merge target must be clarified before deleting remote branches.

## Validation Completed

The following checks passed on this branch:

- Representative Python CI lane:
  - `1288 passed, 21 skipped, 16 xfailed`
- Go kernel/provider lane:
  - `go test ./internal/provider/... ./internal/validator/... ./pkg/hook/... -count=1`
- Product-facing documentation link integrity:
  - `README.md`
  - `CONTRIBUTING.md`
  - `docs/README.md`
- YAML configuration parsing:
  - all `*.yaml` and `*.yml`
- Pytest cache warning cleanup:
  - removed `-c /dev/null` from CI, mutmut, and Codex fast paths
  - no remaining `-c /dev/null` or `/dev/.pytest_cache` patterns in project validation surfaces

## Master Plan Completed In This Branch

Evidence-backed items now completed:

- Product promise and positioning are documented.
- Kernel contract exists in docs, manifest, and contract tests.
- Product zones classify the repository into `core`, `compatibility`, `extensions`, and `experimental`.
- Compatibility layer explicitly distinguishes implemented adapters from documented targets.
- Bootstrap and settings-driver flows are substantially less Claude-first.
- Driver-specific scripts are classified so Claude-only behavior does not masquerade as Codex support.
- Capability-centric routing is enforced in dispatch, gateway selection, skill routing, and metrics.
- Default CI now includes representative contract tests.
- Product-facing docs links fail visibly in automation.

## Remaining Master Plan Work

These are real remaining product-work items, not merge blockers for this branch:

- Classify new runtime additions consistently by zone.
- Reduce central runtime hardcoding of non-core subsystems.
- Map product claims in README/pitch to explicit verification paths.
- Make first-run installation one-pass and lower-friction.
- Improve autodetection and user-facing setup messages.
- Move skills/rules toward canonical-first discovery instead of `.claude/` projection gravity.
- Add visible performance budgets for setup/onboarding flows.
- De-emphasize dashboard, squad, organization, and broad control-plane messaging in top-level docs.
- Freeze, archive, or demote experimental subsystems that compete with the wedge.
- Build canonical proof/demo paths:
  - provider switching without system rewrites
  - real quality gates
  - core usable in minutes
  - easy to adopt, serious to trust
  - resilience under ecosystem churn

## Merge Recommendation

This branch is close to mergeable as a portability/master-plan foundation branch, but do not delete branches yet.

Before merge:

1. Push the current branch so `origin/codex/master-plan-portability` includes the latest commits.
2. Decide whether the target is local `main` or `origin/main`, because they currently differ.
3. Run one final merge dry-run or PR check against the chosen target.
4. Review the large diff intentionally; this branch contains product docs, runtime changes, tests, Codex local artifacts, and generated/driver projection changes.

After merge:

1. Verify `main` contains the branch tip.
2. Push `main` if the remote target is intended to move.
3. Delete `codex/master-plan-portability` locally.
4. Delete `origin/codex/master-plan-portability` only after confirming the remote merge is complete.

## Risk Notes

- The branch is large and crosses runtime, docs, tests, settings projection, and local agent metadata.
- The remaining unchecked master-plan items are mostly product proof, onboarding polish, and complexity-compression work.
- The biggest merge coordination risk is branch topology, not test failure: local `main` and `origin/main` are not equivalent.
