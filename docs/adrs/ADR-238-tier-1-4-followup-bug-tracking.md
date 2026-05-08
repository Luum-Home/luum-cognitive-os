# ADR-238 — Tier 1-4 Follow-Up Bug Tracking

## Status
Pending

<!-- SCOPE: OS -->

**Status**: Pending — 5 open bugs, none yet fixed  
**Date**: 2026-05-07  
**Related**: ADR-218 (history sanitization), ADR-237 (test execution efficiency)

---

## Context

During the Tier 1-4 case-study leak audit (privacy decoupling, commits
`ce8d1ea8` through `8f1c8f00`, 2026-05-07) and the subsequent post-merge
verification pass, five bugs were surfaced. None are blocking the audit's
primary goals (genericizing consumer tokens and fixture service names), but
all are real defects that must be tracked before public release.

This ADR records the bugs with enough detail to reproduce and fix them in
separate PRs. No fixes are applied here.

## Decision

Track each bug as a numbered entry with severity, affected file, reproducer,
proposed remediation, and current status. Fixes are deferred to individual
PRs that reference this ADR.

---

## Bug Registry

### Bug 1 — kpi-trigger.sh writes invalid JSON when reading mock fixtures

**Severity**: MEDIUM  
**File affected**: `scripts/kpi-trigger.sh`  
**Symptom**: When fed mock fixture data (as used in Tier 4 benchmark tests),
the script's JSON output is malformed — likely an unescaped field or missing
comma produced by ad-hoc string concatenation in bash.  
**Discovered**: Tier 4 sub-agent during fixture genericization (commit
`ce8d1ea8` era).

**Reproducer**:
```bash
python3 -m pytest tests/unit/ -k "kpi_trigger" -q
# or, if no unit test yet:
bash scripts/kpi-trigger.sh --fixture tests/fixtures/mock_kpi_input.json | python3 -m json.tool
```

**Proposed remediation**: Replace the ad-hoc JSON construction in
`kpi-trigger.sh` with a `python3 -c` or `jq` pipeline that guarantees
well-formed output; add a unit test that pipes fixture data through the script
and validates JSON with `python3 -m json.tool`.

**Status**: open

---

### Bug 2 — skill-invocation-mandatory.md references missing path

**Severity**: HIGH  
**File affected**: `rules/skill-invocation-mandatory.md`  
**Symptom**: The rule body references `.cognitive-os/sessions/events.jsonl`,
a path that does not exist on a fresh install. The audit test
`test_no_rule_references_missing_file` fails because this path is listed as
required but never created by any initializer.

**Reproducer**:
```bash
python3 -m pytest tests/audit/test_no_rule_references_missing_file.py -q
```

**Proposed remediation**: Either (a) update the reference in
`rules/skill-invocation-mandatory.md` to the actual path created on init, or
(b) add path creation to the `cognitive-os-init` flow so the file exists after
`/cognitive-os-init`. The rule text should not reference paths that only
materialise mid-session.

**Status**: open

---

### Bug 3 — cos-status non-SO branch emits extra `concurrent_write` key

**Severity**: MEDIUM  
**File affected**: `scripts/cos_concurrent_status.py` (or equivalent;
locate via `grep -rln concurrent_write scripts/ lib/`)  
**Symptom**: When executed against a repository that is not a
Shared-Ownership (SO) project, the JSON output contains a `concurrent_write`
key that should only appear in SO contexts. This causes a schema mismatch in
consuming code and breaks the portability test.

**Reproducer**:
```bash
python3 -m pytest tests/red_team/portability/test_cos-coordination-status.py::test_snake_case_python_entrypoint_produces_json -q
```

**Proposed remediation**: Add a guard in `cos_concurrent_status.py` that
omits the `concurrent_write` key (and any other SO-specific keys) when the
project context does not indicate SO mode. Consider a schema variant or a
`--so-context` flag to make the conditional explicit.

**Status**: open

---

### Bug 4 — post-agent-verify snapshot restore emits "base blocked" instead of "baseline blocked"

**Severity**: MEDIUM  
**File affected**: `hooks/post-agent-verify.sh` (locate via
`grep -rln 'base blocked\|baseline blocked' hooks/`)  
**Symptom**: The error message produced when a snapshot restore is blocked
reads "base blocked" — the test assertion expects "baseline blocked". This is
a string-rename regression where the test was updated but the shell script was
not (or vice-versa).

**Reproducer**:
```bash
python3 -m pytest "tests/red_team/portability/post-agent-verify_test.py::test_falsification_out_of_scope_write_restores_from_snapshot" -q
```

**Proposed remediation**: Align the string literal in `post-agent-verify.sh`
with the test expectation ("baseline blocked"). Do a repo-wide grep for both
variants to confirm no other assertion depends on the old wording before
changing.

**Status**: open

---

### Bug 5 — chaos test corrupts lib/targeted_test_resolver.py during test runs

**Severity**: CRITICAL  
**File affected**: `tests/chaos/test_global_verify_regression_catches.py`  
**Symptom**: During the test run, `lib/targeted_test_resolver.py` (149 lines,
real production code) gets overwritten with a 2-line test stub. The test
escapes its tmpdir sandbox and writes into the live source tree. This is the
most severe class of test bug: it silently corrupts production source code,
and any subsequent test run or import will load the stub instead of the real
module.

**Reproducer**:
```bash
python3 -m pytest tests/chaos/test_global_verify_regression_catches.py -q
# then verify:
wc -l lib/targeted_test_resolver.py   # should be 149; if 2, the bug triggered
```

**Proposed remediation**:
1. Identify where the test writes `lib/targeted_test_resolver.py` — replace
   the hardcoded path with a `tmp_path`-relative path or a monkeypatch of the
   module import.
2. Add a fixture-level guard (e.g., `autouse` session-scoped fixture) that
   records and asserts the inode/checksum of `lib/targeted_test_resolver.py`
   before and after each chaos test to catch any future escape.
3. Consider adding `lib/targeted_test_resolver.py` to a read-only
   `PROTECTED_SOURCE_FILES` list checked by a pre-test hook.
4. Restore `lib/targeted_test_resolver.py` from git after confirming the fix:
   `git checkout lib/targeted_test_resolver.py`.

**Status**: open — restore from git immediately if the file has already been
corrupted.

---

## Consequences

All 5 bugs must be resolved before public release:

- **Bug 5** (CRITICAL) is a test-safety violation that may already have
  corrupted the working tree. Verify `lib/targeted_test_resolver.py` line
  count before any further test run. Fix in the next PR.
- **Bug 2** (HIGH) causes a CI audit test to fail on every fresh clone.
  Fix before enabling CI on the public repo.
- **Bugs 1, 3, 4** (MEDIUM) are correctness defects with failing tests.
  Fix before publishing test results as evidence of quality.

Each fix should be a standalone PR referencing ADR-238 in the commit message.
No change to this ADR is required when bugs are fixed — close the tracking
issue (or PR) instead.
