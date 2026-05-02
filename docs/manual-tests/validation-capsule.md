# Manual Test: Validation Capsule

## Goal

Prove that release-lane validation can run without the global hook killswitch and without unrelated Agent snapshot/profile auto-apply mutations.

## Preconditions

- Run from the Cognitive OS repository root.
- Remove `.cognitive-os/runtime/hook-killswitch.flag` if present.
- Decide whether current worktree dirt is intentional.

## Smoke proof

```bash
bash scripts/cos-validation-capsule.sh --allow-dirty --name capsule-smoke -- \
  bash -c 'test "$COS_VALIDATION_MODE" = 1 && test "$COS_SUPPRESS_AGENT_SNAPSHOT" = 1 && test "$COS_DISABLE_PROFILE_AUTOAPPLY" = 1'
```

Expected:

- exit code `0`
- a summary under `.cognitive-os/reports/validation-capsules/latest/summary.txt`
- summary lists the scoped guards

## E2E proof

```bash
bash scripts/cos-validation-capsule.sh --allow-dirty --name e2e -- \
  env COS_ALLOW_DOCKER_TESTS=1 ./cos-test cluster --lane e2e
```

Expected:

- no global killswitch is created
- E2E hooks under test still run
- if the worktree changes, the capsule exits `3` unless `--allow-mutation` was explicit

## Integration proof

```bash
bash scripts/cos-validation-capsule.sh --allow-dirty --name integration -- \
  ./cos-test cluster --lane integration
```

Expected:

- command output is captured in `full-output.txt`
- before/after status is captured
- tracked mutation is visible in `git-status-diff.txt`
