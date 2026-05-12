---
adr: 278
title: subprocess.run Timeout Discipline
status: accepted
implementation_status: partial
classification_basis: 'Audit + allowlist + test-default shipped; per-call backfill (984 of 1824 calls) tracked as Phase 2.'
date: 2026-05-12
supersedes: []
superseded_by: null
extends: [ADR-248, ADR-275, ADR-277]
implementation_files:
  - scripts/cos-subprocess-timeout-audit.py
  - manifests/subprocess-timeout-allowlist.yaml
  - tests/conftest.py
  - tests/red_team/portability/test_cos-subprocess-timeout-audit.py
tier: maintainer
tags: [tests, subprocess, timeout, hang-prevention, control-plane, postmortem-2026-05-12]
---
# ADR-278: subprocess.run Timeout Discipline

## Status

Accepted — audit + allowlist + test-default shipped 2026-05-12. Per-call
backfill of the 984 untimed call sites tracked as Phase 2 follow-up.

<!-- SCOPE: OS -->

**Date**: 2026-05-12

## Context

The 2026-05-12 verification pass on the `tests/contracts/` + `tests/audit/`
suites hung at ~8% completion. Root cause investigation found:

- **174 `subprocess.run(...)` calls** across tests/contracts/ + tests/audit/
- **169 of those (97%) omit `timeout=`**
- Two specific tests hung indefinitely on subprocess calls that never
  returned: `test_repository_family_ledgers_cover_hooks_skills_and_rules`
  and `test_cos_primitive_surface_coverage_alias_json_exit_code_contract`
- pytest's `--timeout-method=thread` cannot kill an OS subprocess spawned
  without `subprocess.run(timeout=...)` — the test thread is killed but
  the subprocess keeps the file descriptors and blocks suite teardown

Widening the scan to production:

- **1824 total `subprocess.run(...)` calls** across `scripts/`, `hooks/`,
  `lib/`, `tests/`, `packages/`
- **984 (54%) omit `timeout=`**
- 97 unique files contain at least one untimed call

This is the same anti-pattern that motivated ADR-273 (silent state
proliferation): a convention that "everyone should remember" but nothing
enforces.

## Decision

Establish a discipline for `subprocess.run` timeout usage with three
layers of enforcement, mirroring the ADR-274 audit pattern.

### 1. Convention (the rule)

Every `subprocess.run(...)` call in `scripts/`, `hooks/`, `lib/`, `tests/`,
or `packages/` MUST include an explicit `timeout=` keyword OR appear in
`manifests/subprocess-timeout-allowlist.yaml` with rationale.

Exemptions live in the allowlist:
- Interactive subprocess streaming stdout to user
- Long-running watchers/servers/REPLs
- Commands with known-bounded execution that has its own deadline (rare)

The bias is **"add timeout=, justify omission"**.

### 2. Audit (Phase 1, this ADR)

`scripts/cos-subprocess-timeout-audit.py` scans the repo, emits
findings in the control-plane runner shape:

- `total_calls`, `timed_calls`, `untimed_calls`, `allowlisted_calls`,
  `coverage_pct`
- One `warn` finding per untimed-non-allowlisted call with
  stable_id `adr-278/subprocess-timeout/<rel>:<line>`
- Schema: `subprocess-timeout-audit/v1`

Wired into `manifests/control-plane-audits.yaml` as
`subprocess-timeout-coverage` in hourly + pre-public lanes.

### 3. Test-tier safety net (Phase 1, this ADR)

`tests/conftest.py` monkey-patches `subprocess.run` at module load to
inject `timeout=45` when the caller omits it. Configurable via
`COS_TEST_SUBPROCESS_DEFAULT_TIMEOUT` (set to 0 to disable). Explicit
per-call timeouts override.

This unblocks the suite IMMEDIATELY without backfilling all 169 test
calls; the audit + allowlist provide the per-call discipline that
backfilling will eventually satisfy.

### 4. Pre-commit gate (Phase 2, follow-up)

Future: extend `.githooks/pre-commit` to scan newly staged Python files
for new `subprocess.run(...)` calls without `timeout=` and block. Today
the audit reports them; the gate would prevent regression on new code.

### 5. Backfill (Phase 2, follow-up)

The first audit run produces a 984-item backlog. Backfill is opt-in
per area; priorities:

- **P0** — files in `scripts/cos-*` (operator-facing CLI; hangs affect
  every session)
- **P1** — files in `hooks/` (PreToolUse/PostToolUse hooks; hangs
  block the harness chain)
- **P2** — `lib/` and `tests/` (test-tier is partially covered by the
  conftest safety net)

## Operational Guide

### What changes for the operator

| Surface | Before | After |
|---|---|---|
| Test suite hangs on subprocess | suite blocked indefinitely | conftest injects timeout=45, test fails with `subprocess.TimeoutExpired` instead of hanging |
| New subprocess.run() in code review | reviewer must remember to ask about timeout | audit flags it on next control-plane run; pre-commit gate planned for Phase 2 |
| Intentional omission (server/REPL) | implicit, can be missed | declared in `manifests/subprocess-timeout-allowlist.yaml` with rationale + owner |

### Daily operational pattern

1. Author writes new code with `subprocess.run(...)`. Default: include `timeout=`.
2. If omission is required (e.g., interactive stdout streaming): add entry to
   `manifests/subprocess-timeout-allowlist.yaml` with rationale.
3. Audit runs on every control-plane hourly cycle; new untimed calls become
   `warn` findings with stable_id `adr-278/subprocess-timeout/<path>:<line>`.
4. Test-tier: the conftest default kicks in transparently if author forgets.
5. Periodic backfill: pick a file from `cos-subprocess-timeout-audit` output,
   add explicit timeouts, drop the audit findings.

### Reading guide for cold readers

1. Run `python3 scripts/cos-subprocess-timeout-audit.py | jq .summary` to see
   the current state of compliance.
2. Read this ADR §Decision for the contract.
3. The allowlist at `manifests/subprocess-timeout-allowlist.yaml` is the
   single source of truth for "this omission is intentional".
4. The test-tier safety net lives in `tests/conftest.py` (look for
   `_DEFAULT_TEST_SUBPROCESS_TIMEOUT`).

## Consequences

- **Hangs are bounded**: a buggy subprocess raises `TimeoutExpired` after
  the configured timeout, instead of blocking the caller indefinitely.
- **Reviewable convention**: reviewer can grep + see allowlist; intent is
  declared, not implicit.
- **Visible debt**: the 984-call backfill is quantified, not hidden.
- **Cost**: an explicit timeout is one keyword argument per call site;
  marginal cost is zero, the backfill cost is bounded.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Monkey-patch subprocess.run in production too | Hides bugs behind a default; better to surface omission and let author justify the timeout choice. |
| Single global default timeout for all callers | Different operations have legitimately different deadlines; one-size-fits-all degrades both fast and slow paths. |
| Just rely on test-tier conftest | Production scripts (hooks, CLI) still hang; safety net only covers pytest. |
| Add a lint rule (ruff/flake8) | Ruff has no built-in rule for keyword-presence; custom AST check is what the audit script already provides. |

## Verification

```bash
# Audit
python3 scripts/cos-subprocess-timeout-audit.py --strict
# Expected: exit 2 today (984 untimed). After backfill: exit 0.

# Test-tier safety net (already shipped):
python3 -m pytest tests/contracts/ -q --timeout=60
# Should now COMPLETE the suite (or at worst surface real test failures)
# instead of hanging indefinitely.

# Allowlist entry shape:
cat manifests/subprocess-timeout-allowlist.yaml
```

## Follow-ups

- **Phase 2**: pre-commit gate blocking new `subprocess.run(...)` without
  `timeout=` in staged files.
- **Phase 2**: backfill P0 + P1 (scripts/cos-* + hooks/).
- **Phase 3**: extend audit to Go (`exec.Command`) and shell (`bash -c`
  with no timeout flag) so the discipline is language-agnostic.

## Related

- ADR-248 — Control-plane audit loop (this audit registers there)
- ADR-273 — Pending truth ledger (untimed calls become audit-finding ledger items)
- ADR-275 — Closure & projection (the projector surfaces this audit's coverage_pct)
- ADR-277 — Documentation truth control (a claim in the manifest forbids stale
  phrases like "subprocess.run with no timeout is harmless")
- `docs/architecture/pending-truth-architecture.md` — 4-layer map
