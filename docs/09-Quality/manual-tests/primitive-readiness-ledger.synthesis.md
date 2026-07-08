---
type: quality-synthesis
source: docs/09-Quality/manual-tests/primitive-readiness-ledger.md
provenance: "Manual test proving a future agent or operator can regenerate and use the machine-readable script readiness ledger without relying on conversation context."
---

## What it is
A manual test for `scripts/primitive_readiness_ledger.py`, which classifies every script primitive by role (e.g. `agentic-primitive`, `maintainer-tool`, `driver-specific`, `migration-only`) and consumer accessibility, and tracks a zero-tolerance lifecycle-metadata backlog (ADR-126) for agentic primitives.

## Key mechanics
- Step 1: regenerate the ledger via `python3 scripts/primitive_readiness_ledger.py --project-dir .`.
- Step 2: load `docs/06-Daily/reports/primitive-readiness-ledger-scripts-latest.json`, assert `target_family == 'scripts'`, `total_scripts > 0`, `consumer_accessibility` present in summary, every script row's `role` is in `allowed_roles`, and every row has non-empty `consumer_accessibility`.
- Step 3: load the lifecycle backlog at `docs/06-Daily/reports/primitive-readiness-lifecycle-backlog-scripts-latest.json`, assert `purpose == 'agentic primitives missing ADR-126 lifecycle metadata'` and `summary['total'] == 0` — i.e. the backlog is a ratchet that must stay at zero.
- Step 4: inspect the first 40 lines of the Markdown report.
- Step 5: manually pick three rows (one each from `agentic-primitive`, `maintainer-tool`, and either `driver-specific` or `migration-only`) and confirm each has a believable `role_source`, `confidence`, evidence, consumers, `consumer_accessibility`, and next action.
- Step 6: confirm consumer accessibility isn't inferred from SO-local docs alone — assert `consumer_accessibility['install-profile-managed'] > 0` and that at least one row has accessibility `so-local-only` or `skill-referenced-not-projectable`.
- Step 7: run `tests/unit/test_primitive_readiness_ledger.py` and `tests/contracts/test_primitive_readiness_ledger_contract.py`.
- Expected result: JSON/Markdown reports exist; every row has an allowed role and consumer-accessibility metadata; the lifecycle-metadata-missing count for scripts stays at zero after the ratchet; low-confidence rows remain visible but don't fail the default command; optional fail flags are reserved for a later ratchet, not the initial adoption gate.

## Relations & where used
Depends on `scripts/primitive_readiness_ledger.py`, feeding `docs/06-Daily/reports/primitive-readiness-ledger-scripts-latest.{json,md}` and the ADR-126-linked lifecycle backlog report. Sibling to `primitive-duplication-audit.md` and `primitive-harness-coverage.md` in the same primitive-audit family.

## Status / caveats
Explicit non-claim: this test does not prove every script is correctly promoted or retired — it proves the ledger exists, is complete, and is usable as the next triage surface. No dated snapshot or inconsistency found.
