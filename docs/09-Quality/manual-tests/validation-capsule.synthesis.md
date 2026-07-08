---
type: quality-synthesis
source: docs/09-Quality/manual-tests/validation-capsule.md
provenance: "Proves release-lane validation can run scoped, without the global hook killswitch and without unrelated Agent snapshot/profile auto-apply mutations leaking into the run."
---

## What it is
A manual test for the validation-capsule mechanism (`scripts/cos-validation-capsule.sh`), which wraps a command so it runs with scoped safety guards instead of the blunt global hook killswitch.

## Key mechanics
- **Preconditions**: run from repo root; remove `.cognitive-os/runtime/hook-killswitch.flag` if present; decide whether current worktree dirt is intentional.
- **Smoke proof**: `cos-validation-capsule.sh --allow-dirty --name capsule-smoke -- bash -c '...'` asserts the scoped env vars `COS_VALIDATION_MODE=1`, `COS_SUPPRESS_AGENT_SNAPSHOT=1`, `COS_DISABLE_PROFILE_AUTOAPPLY=1` are set inside the capsule; expects exit 0 and a summary at `.cognitive-os/reports/validation-capsules/latest/summary.txt` listing the scoped guards.
- **E2E proof**: `cos-validation-capsule.sh --allow-dirty --name e2e -- env COS_ALLOW_DOCKER_TESTS=1 ./cos-test cluster --lane e2e`; expects no global killswitch created, E2E hooks still run under test, and the capsule exits `3` on worktree mutation unless `--allow-mutation` was passed.
- **Integration proof**: `cos-validation-capsule.sh --allow-dirty --name integration -- ./cos-test cluster --lane integration`; expects command output captured in `full-output.txt`, before/after status captured, and tracked mutation visible in `git-status-diff.txt`.

## Relations & where used
Underpins release-lane validation used across other quality proofs (e.g. `worktree-sweeper.md` references safe temp-worktree handling in a similar spirit); the capsule mechanism is the scoped alternative to the coarser global hook killswitch flag.

## Status / caveats
No dated evidence block embedded — this is a repeatable procedure spec, not a logged historical run.
