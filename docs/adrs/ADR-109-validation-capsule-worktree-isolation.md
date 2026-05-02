# ADR-109: Validation Capsule Worktree Isolation

## Status

Accepted — 2026-05-02.

## Context

Cognitive OS validates itself with hooks, settings projection, installer flows, live audit flows, and Agent lifecycle primitives enabled. This makes self-hosted validation powerful but risky: the validation run can trigger the same automation it is testing.

The 2026-05-02 release-lane investigation exposed this failure mode:

- `pre-agent-snapshot.sh` can run before Agent tool calls and use `git stash push --keep-index` for tracked changes.
- `profile-drift-autoapply.sh` can run on `SessionStart` and rewrite harness settings if profile drift is detected.
- Full integration can exercise live flows that create docs, reports, plans, or package artifacts.
- A manual global killswitch suppressed mutation but also suppressed hooks under E2E test, producing false failures.

ADR-072 defines lane taxonomy and ADR-100 governs resources. This ADR adds worktree isolation for release validation.

## Decision

Introduce a validation capsule primitive implemented by `scripts/cos-validation-capsule.sh`.

The capsule:

1. Records before/after `git status --porcelain=v1`.
2. Refuses to run while `.cognitive-os/runtime/hook-killswitch.flag` exists.
3. Exports scoped validation guards:
   - `COS_VALIDATION_MODE=1`
   - `COS_SUPPRESS_AGENT_SNAPSHOT=1`
   - `COS_DISABLE_PROFILE_AUTOAPPLY=1`
4. Captures command output and validation metadata under `.cognitive-os/reports/validation-capsules/`.
5. Fails with exit code `3` when the command succeeds but changes the worktree without explicit `--allow-mutation`.

Update relevant hooks:

- `pre-agent-snapshot.sh` exits early when `COS_SUPPRESS_AGENT_SNAPSHOT=1` or `COS_VALIDATION_MODE=1`.
- `profile-drift-autoapply.sh` exits early when `COS_VALIDATION_MODE=1` or `COS_DISABLE_PROFILE_AUTOAPPLY=1`.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Use the global hook killswitch | It invalidates E2E proofs by suppressing hooks under test. |
| Always run validation in a separate git worktree without a capsule lock | Useful but insufficient because source-side hooks can still race and operators need a single safe local command for targeted reproduction. |
| Disable all hooks during tests | E2E and integration lanes are intended to prove hook behavior. |
| Rely on manual `git stash` before every long run | Stashing was part of the confusing behavior; the validation boundary must be explicit, logged, and testable. |

## Consequences

### Positive

- E2E hook tests no longer require the global killswitch.
- Agent snapshot protection remains active in normal sessions but is suppressed in validation.
- Settings projection auto-repair remains active in normal sessions but is suppressed in validation.
- Worktree mutation becomes visible in every capsule artifact.

### Negative

- Operators must learn one more validation command.
- Some tests that intentionally update repository artifacts must pass `--allow-mutation` and justify it.
- The capsule cannot protect against host-level hooks outside the child command environment; those require harness-level environment support.

## Enforcement

- `tests/unit/test_validation_capsule.py` verifies capsule env propagation.
- `tests/unit/test_validation_capsule.py` verifies `pre-agent-snapshot.sh` does not stash dirty work when suppressed.
- `scripts/cos-validation-capsule.sh` refuses to run with the global killswitch active.

## Verification

```bash
python3 -m pytest tests/unit/test_validation_capsule.py -q
make test-laptop
```

## References

- [Validation Worktree Mutation Postmortem — 2026-05-02](../reports/validation-worktree-mutation-postmortem-2026-05-02.md)
- [Validation Capsule](../architecture/validation-capsule.md)
- [ADR-072: Test Lane Taxonomy & Escalation Ladder](ADR-072-test-lane-taxonomy.md)
- [ADR-100: Test Resource Governance](ADR-100-test-resource-governance.md)
