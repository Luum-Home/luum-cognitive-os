---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/chaos-test-isolation.md
provenance: "Documents the ADR-245 isolation guarantee for chaos tests — that simulated failures must never leave mutated production source files behind — and how to diagnose/fix violations."
---

## What it is

A short runbook (ADR-245) establishing the rule that chaos tests, which simulate failures/crashes/corrupted runtime state, must not mutate production source files in the operator's checkout, plus the enforcement mechanism and platform-specific hardening notes.

## Key mechanics

- **Default portable mode**: `tests/chaos/conftest.py` installs an autouse fixture, `chaos_readonly_workspace`, that snapshots `lib/`, `scripts/`, and `hooks/` before each chaos test and re-walks them at teardown. Any modified/deleted/added file is restored immediately and the test is failed with the file name; `__pycache__`/bytecode artifacts are ignored. This is detect-and-restore (post-hoc), not prevention.
- **Guidance for test authors**: use fixture copies, tempdirs, or dependency injection to simulate broken source-like behavior instead of touching real files.
- **Linux strict mode (future)**: proposed to run chaos tests inside a read-only bind/mount sandbox (`bwrap --ro-bind` or equivalent) that fails at write-time with an OS error rather than waiting for teardown restore.
- **macOS strict mode**: recommends a copy-on-write worktree or temp checkout with write bits removed from protected directories for the test process duration — explicitly warns against chmod-ing the operator's primary checkout.
- **Diagnostic signature**: a failure message like `ADR-245 chaos_readonly_workspace restored production-source mutation(s): modified-restored:lib/example.py` means the guard caught and undid a mutation before the next test ran. The prescribed fix is to move the mutation into a temp fixture copy — explicitly NOT to add a broad allowlist for production source.

## Relations & where used

Enforced via the `chaos_readonly_workspace` autouse fixture in `tests/chaos/conftest.py`, which all chaos tests inherit implicitly.

## Status / caveats

The "Linux strict mode" section is explicitly forward-looking ("Future CI lanes may run...") — it describes a not-yet-implemented hardening path, not current behavior; only the portable (macOS/laptop-safe) restore-at-teardown mode is confirmed as the operative floor. No internal inconsistencies found.
