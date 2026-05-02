# Validation Capsule

## Purpose

A validation capsule is the Cognitive OS operator primitive for running release or diagnostic commands without allowing unrelated session automation to mutate the active worktree.

It is narrower than the global hook killswitch: hooks under test keep running, while validation-hostile mutators such as Agent snapshots and profile auto-apply are suppressed.

## Command

```bash
bash scripts/cos-validation-capsule.sh --allow-dirty --name e2e -- \
  env COS_ALLOW_DOCKER_TESTS=1 ./cos-test cluster --lane e2e
```

For clean release proof, omit `--allow-dirty`.

## Scoped guards

| Variable | Effect |
|---|---|
| `COS_VALIDATION_MODE=1` | Declares a child command is running inside a validation capsule. |
| `COS_SUPPRESS_AGENT_SNAPSHOT=1` | Suppresses `pre-agent-snapshot.sh` so it cannot stash tracked work. |
| `COS_DISABLE_PROFILE_AUTOAPPLY=1` | Suppresses profile drift auto-apply so settings are not rewritten during validation. |
| `COS_VALIDATION_CAPSULE_DIR` | Points at the current capsule artifact directory. |

## Why not the global killswitch?

`.cognitive-os/runtime/hook-killswitch.flag` suppresses non-critical hooks. That is appropriate for emergencies, but invalidates E2E proofs. If it suppresses `session-watchdog-launcher.sh`, tests expecting `session-watchdog.pid` fail for the wrong reason.

The capsule refuses to run while the global killswitch file exists.

## Artifacts

Each run writes to `.cognitive-os/reports/validation-capsules/<timestamp>-<name>/`:

- `command.txt`
- `env.txt`
- `full-output.txt`
- `git-status-before.txt`
- `git-status-after.txt`
- `git-status-diff.txt`
- `summary.txt`
- `exit-code.txt`

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Command passed and worktree state did not change, or mutation was explicitly allowed. |
| `2` | Capsule preflight or usage failure. |
| `3` | Command passed but changed the worktree without `--allow-mutation`. |
| other | Underlying command exit code. |

## Recommended release-lane use

```bash
bash scripts/cos-validation-capsule.sh --allow-dirty --name smoke -- ./cos-test cluster --lane smoke
bash scripts/cos-validation-capsule.sh --allow-dirty --name e2e -- env COS_ALLOW_DOCKER_TESTS=1 ./cos-test cluster --lane e2e
bash scripts/cos-validation-capsule.sh --allow-dirty --name integration-docker -- env COS_ALLOW_DOCKER_TESTS=1 ./cos-test cluster --lane integration-docker
bash scripts/cos-validation-capsule.sh --allow-dirty --name integration -- ./cos-test cluster --lane integration
```

Use `--allow-mutation` only when the test's purpose is to update repository artifacts.
