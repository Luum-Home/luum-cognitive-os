---

adr: 245
title: Chaos Tests Run with Read-Only Production Source
status: accepted
implementation_status: implemented
classification_basis: 'chaos read-only workspace fixture and regression tests satisfy the ADR source-protection scope'
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-238]
implementation_files:
  - tests/chaos/conftest.py
  - tests/chaos/test_global_verify_regression_catches.py
  - docs/runbooks/chaos-test-isolation.md
tier: maintainer
tags: [testing, safety, chaos, postmortem-2026-05-08]
---
# ADR-245: Chaos Tests Run with Read-Only Production Source

## Status

Accepted — Slice A implemented. `tests/chaos/conftest.py` installs `chaos_readonly_workspace`, restores source mutations under `lib/`, `scripts/`, and `hooks/`, and tests cover restore/remove/ignore behavior plus the original global-verify regression path. Drafted during the 2026-05-08 pre-public readiness session after
a chaos test was discovered overwriting production source files mid-run.
Requires operator review before implementation.

## Context

Bug #5 of the ADR-238 follow-up cluster was a chaos test that mutated the
working tree during execution. Specifically,
`tests/chaos/test_global_verify_regression_catches.py` overwrote
`lib/targeted_test_resolver.py` (149 lines of production code) with a
two-line stub in order to simulate a regression. The mutation was
visible to every subsequent test, every subsequent command in the same
session, and to any concurrent agent reading the same checkout.

This is the worst class of test bug: a test that silently mutates the
source tree. It cannot be caught by ordinary review because the
mutation only manifests during the test's own execution. The ad-hoc fix
that landed in ADR-238 follow-up was to inject a fake resolver via an
environment variable. The fix is correct for that one test, but the bug
*class* should not be reachable by construction.

Observed symptoms on 2026-05-08:

- A 149-line production module was replaced by a 2-line stub during a
  chaos test run; the diff was not reverted on test teardown.
- The mutation broke unrelated test files in the same session because
  imports of the resolver returned the stub.
- A concurrent agent reading the same checkout observed an inconsistent
  module body; this is exactly the cross-session contamination class
  ADR-239 is correcting at the worktree layer.
- The test that detected the regression of the resolver (the test the
  chaos test was simulating) was the same module the chaos test
  destroyed. The contradiction was invisible to ordinary CI.

## Decision

Chaos tests run with `lib/`, `scripts/`, and `hooks/` enforced read-only
for the duration of each chaos test. The enforcement is implemented as a
pytest autouse fixture in `tests/chaos/conftest.py`:
`chaos_readonly_workspace`.

Implementation strategy, ordered by portability:

1. **Default (portable, snapshot-and-revert).** Before each chaos test,
   the fixture computes `(inode, sha256, size, mtime_ns)` for every file
   under the protected directories and stores the tuple in memory. After
   the test, the fixture re-walks the same set; any file whose tuple
   changed is **reverted from a known-good snapshot** stored in a
   tempdir, and the test is marked failed with a loud assertion that
   names the file and the diff. This catches the bug class without
   requiring root or platform-specific mounts.
2. **Opt-in (Linux, mount-based).** When run in CI under the
   `chaos-strict` lane, the fixture uses `bwrap --ro-bind` (or
   `mount --bind -o ro` when bwrap is not available) to make the
   protected directories actually read-only at the kernel level. The
   test process gets `EROFS` on any write attempt, so the bug fails
   immediately rather than at teardown.
3. **macOS opt-in.** A `chmod -R u-w` over a copy-on-write clone of the
   protected directories provides the same property without requiring
   `mount`. Documented as the macOS path in the runbook.

The runbook at `docs/runbooks/chaos-test-isolation.md` describes both
modes, when to use each, and the diagnostic surface when a chaos test
trips the protection.

`tests/chaos/test_global_verify_regression_catches.py` reverts the
ad-hoc env-var workaround from ADR-238 follow-up and uses the proper
fixture. The simulated regression is injected into a *test fixture*
copy of the resolver, not the production module.

## Operational Guide

### What changes for the operator

Before this ADR, chaos tests could write to `lib/`, `scripts/`, or `hooks/`
during a test run. The mutation persisted after the test, affected subsequent
imports in the same session, and could contaminate concurrent agents reading
the same checkout. There was no automatic detection or revert.

After this ADR, the `chaos_readonly_workspace` autouse fixture in
`tests/chaos/conftest.py` enforces read-only protection for `lib/`, `scripts/`,
and `hooks/` for every chaos test:

- **Default (all platforms):** The fixture snapshots file fingerprints before
  the test. After the test, any file whose fingerprint changed is reverted from
  a tempdir copy and the test is marked failed with a named-file assertion and
  diff.
- **Linux `chaos-strict` lane (opt-in):** `bwrap --ro-bind` makes the
  protected directories genuinely read-only at the kernel level; writes produce
  `EROFS` immediately.
- **macOS opt-in:** A `chmod -R u-w` over a copy-on-write clone provides the
  same guarantee without `mount`.

The operator does not need to invoke anything. Protection is automatic for the
`tests/chaos/` lane via the autouse fixture.

### What this answers (and what it doesn't)

**Answers:**
- "Can a chaos test silently overwrite a production module?" — No. Either the
  test fails loudly at teardown (portable mode) or the write is rejected
  immediately (`chaos-strict` mode).
- "Which file was mutated and what changed?" — The assertion message names the
  file and includes the diff.
- "Does this protect all write paths?" — Yes. The snapshot-and-revert catches
  all write mechanisms (`open`, `pathlib`, `shutil`, subprocess shell,
  `os.rename`), not just explicit `open(..., 'w')` calls.

**Does not answer:**
- Whether a chaos test that legitimately needs a temporary file under `lib/`
  is correct to do so. Such tests would need to declare an explicit allow-list
  and use a tempdir overlay (no current examples identified).
- Whether mutations outside `lib/`, `scripts/`, and `hooks/` are safe.
  Protection scope is fixed to those three directories in Slice A.

### Daily operational pattern

1. Run chaos tests normally — protection is automatic:
   ```bash
   python3 -m pytest tests/chaos/ -q
   ```
2. If a chaos test fails with a "protected file mutated" assertion, the
   failing test's teardown logs the file name and diff. Fix the test to
   inject the regression via a fixture copy instead of writing to the
   production module.
3. To verify the fixture is installed:
   ```bash
   python3 -m pytest tests/chaos/test_global_verify_regression_catches.py -q
   test -f docs/runbooks/chaos-test-isolation.md
   ```
4. For CI runs where `bwrap` is available and you want immediate-failure
   semantics, run under the `chaos-strict` lane. See
   `docs/runbooks/chaos-test-isolation.md` for the exact invocation.

### Reading guide for cold readers

If you encounter this ADR without session context:

1. The bug that motivated this ADR: `tests/chaos/test_global_verify_regression_catches.py`
   replaced `lib/targeted_test_resolver.py` (149 lines of production code)
   with a 2-line stub during a test run on 2026-05-08. The mutation was not
   reverted and broke unrelated tests.
2. The fix is in `tests/chaos/conftest.py` — look for `chaos_readonly_workspace`.
3. The runbook at `docs/runbooks/chaos-test-isolation.md` describes both
   execution modes and diagnostic steps when the protection trips.
4. The protection scope is intentionally limited to `lib/`, `scripts/`, and
   `hooks/` — not the entire working tree — to keep the snapshot cost small.

## Alternatives rejected

- **Keep the env-var workaround and call it good** — rejected because it
  fixes one test. The bug class — chaos tests mutating production
  source — is not closed and will recur the next time a contributor
  writes a chaos test that needs to simulate a regression.
- **Run chaos tests in a fully containerized VM** — rejected as the
  default because the cost (image build, slow startup, CI-only
  applicability) is disproportionate to the bug class. It remains a
  valid opt-in for a future `chaos-strict-ci` lane but should not be
  the floor.
- **Static-analysis lint that forbids `open(..., 'w')` on `lib/`,
  `scripts/`, `hooks/` from chaos test files** — rejected because
  mutation can be reached through `pathlib.Path.write_text`,
  `shutil.copy`, subprocess shell, or `os.rename`. A runtime check
  catches all paths; a lint catches one syntactic spelling.
- **Trust convention plus code review** — rejected because the
  2026-05-08 mutation passed code review and CI for an unknown
  duration before the operator-driven session caught it. Convention is
  not a control surface.

## Consequences

### Positive

- A chaos test that mutates a protected file fails loudly at teardown
  with the file name and diff, and the file is restored before the
  next test runs.
- The `chaos-strict` opt-in turns the failure into an immediate
  `EROFS`, which is the most diagnostic possible signal.
- The test that simulated the regression of the resolver is now
  written against a fixture copy and cannot collide with the
  production module again.

### Negative

- The snapshot-and-revert path computes `sha256` for every file under
  three directories on every chaos test. For this repository the cost
  is small; for very large trees it would need to be scoped further.
- Two execution modes (portable vs. mount-based) are two surfaces to
  keep in sync; the runbook is the authoritative description.
- Chaos tests that legitimately need to write under `lib/` (none
  identified today) would need to declare an explicit allow-list and
  use a tempdir overlay.

## Acceptance criteria

1. `tests/chaos/conftest.py` defines `chaos_readonly_workspace` as an
   autouse fixture for the chaos lane.
2. A test that writes any byte to `lib/`, `scripts/`, or `hooks/`
   during a chaos run fails with a clear, file-named assertion and the
   tree is reverted before the next test.
3. `tests/chaos/test_global_verify_regression_catches.py` no longer
   relies on the env-var workaround from ADR-238 follow-up.
4. `docs/runbooks/chaos-test-isolation.md` documents the portable mode
   and the Linux/macOS opt-in modes.
5. A deliberately-broken chaos test that writes to `lib/` is rejected
   in CI with a non-zero exit and a diagnostic message naming the
   protected file.

## Verification

```bash
python3 -m pytest tests/chaos/ -q
python3 -m pytest tests/chaos/test_global_verify_regression_catches.py -q
test -f docs/runbooks/chaos-test-isolation.md
```
