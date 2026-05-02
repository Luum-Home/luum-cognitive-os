# Validation Worktree Mutation Postmortem — 2026-05-02

## Status

Resolved by ADR-109 and the validation capsule implementation.

## Summary

Optional release-lane validation was run in the active Cognitive OS worktree while session and Agent lifecycle agentic primitives were enabled. The validation run exercised hooks that can legitimately mutate local state, and some integration tests also generated source-adjacent artifacts. This made it difficult to distinguish product failures from validation-harness interference.

A global hook killswitch was then used manually to stop mutation during debugging. That created an artificial E2E failure because the same killswitch suppressed hooks under test, including the SessionStart watchdog launcher.

## Impact

- The operator could not trust whether all failures were real product defects.
- Some edits appeared to revert to base when snapshot/stash behavior interacted with unstaged tracked files.
- The E2E lane produced false negatives when the global killswitch suppressed SessionStart hooks.
- Integration consumed nearly the full extended timeout before exposing both real failures and worktree-contamination side effects.

## Timeline

1. Optional lanes outside `make test-all` were executed: `integration`, `integration-docker`, `e2e`, `smoke`, `arena`, `benchmark`, and `quality`.
2. E2E exposed a real parser bug: wrapped SessionStart commands were parsed as wrapper paths plus arguments.
3. Integration Docker exposed a real compose-contract bug: Paperclip was validated without its `legacy` profile.
4. Empty reserved lanes exposed a test-runner semantics gap: pytest exit `5` was treated as release failure.
5. Full integration and E2E validation dirtied the worktree through live flows and active session automation.
6. A global killswitch was manually enabled to reduce mutation.
7. E2E failed artificially because the killswitch also suppressed hooks being tested.
8. The fix direction became clear: validation needs scoped suppression, not emergency shutdown.

## Root causes

### No worktree isolation boundary for release validation

ADR-072 defines lanes and ADR-100 governs resources, but neither defines how a validation run protects the active worktree from unrelated session automation.

### Global killswitch used as a validation tool

The global hook killswitch is an emergency stop. It is too broad for E2E because E2E is supposed to prove those hooks run.

### Agent snapshot primitive is correct in normal use but hostile to validation

`pre-agent-snapshot.sh` uses `git stash push --keep-index` for tracked dirty files. That protects real Agent launches, but during validation it can make unstaged work appear to vanish or return to base.

### Profile auto-apply is useful in sessions but surprising in validation

`profile-drift-autoapply.sh` can re-run the efficiency profile and rewrite harness settings on SessionStart. During validation, those rewrites look like test contamination unless they are explicitly suppressed and logged.

## Corrective actions

- Add `scripts/cos-validation-capsule.sh` as the standard validation wrapper.
- Make `pre-agent-snapshot.sh` respect `COS_SUPPRESS_AGENT_SNAPSHOT=1` and `COS_VALIDATION_MODE=1`.
- Make `profile-drift-autoapply.sh` respect `COS_VALIDATION_MODE=1`.
- Refuse validation-capsule runs while the global killswitch file exists.
- Capture before/after `git status --porcelain=v1` for every capsule run.
- Add unit coverage for capsule env propagation and snapshot suppression.

## What changes operationally

Operators should run stateful release lanes through the capsule instead of toggling `.cognitive-os/runtime/hook-killswitch.flag`:

```bash
bash scripts/cos-validation-capsule.sh --allow-dirty --name e2e -- \
  env COS_ALLOW_DOCKER_TESTS=1 ./cos-test cluster --lane e2e
```

## Lessons

- Validation isolation must be a first-class primitive.
- Emergency shutdown and test isolation are different controls.
- Long-running lanes need both resource governance and worktree governance.
