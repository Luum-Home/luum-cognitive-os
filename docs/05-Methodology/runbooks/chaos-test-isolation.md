# Chaos Test Isolation Runbook (ADR-245)

Chaos tests may simulate failures, crashes, and corrupted runtime state. They may
not mutate production source files in the operator checkout.

## Default portable mode

`tests/chaos/conftest.py` installs the `chaos_readonly_workspace` autouse
fixture. For each chaos test it snapshots files under:

- `lib/`
- `scripts/`
- `hooks/`

At teardown it re-walks those directories. Any modified/deleted/added file is
restored immediately and the test fails with the file name. `__pycache__` and
bytecode artifacts are ignored.

Use fixture copies, tempdirs, or dependency injection when a chaos test needs to
simulate broken source-like behavior.

## Linux strict mode

Future CI lanes may run chaos tests inside a read-only bind/mount sandbox
(`bwrap --ro-bind` or equivalent). That mode should fail at write time with an
OS error instead of waiting for teardown. The portable fixture remains the floor
because it works on macOS and local laptops without elevated privileges.

## macOS strict mode

Use a copy-on-write worktree or temp checkout and remove user write bits from
protected directories for the duration of the test process. Do not chmod the
operator's primary checkout.

## Diagnostics

A failure like this means the guard restored a mutation before the next test ran:

```text
ADR-245 chaos_readonly_workspace restored production-source mutation(s):
modified-restored:lib/example.py
```

Fix the test by moving the mutation into a temp fixture copy. Do not add a broad
allowlist for production source.
