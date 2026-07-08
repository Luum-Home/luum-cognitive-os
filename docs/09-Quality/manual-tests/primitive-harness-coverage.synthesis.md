---
type: quality-synthesis
source: docs/09-Quality/manual-tests/primitive-harness-coverage.md
provenance: "Manual test proving scope classification and surface implementation coverage are separate, inspectable axes across IDE harnesses, CLI, shell-CI, UI, and reports — preventing conflation of scope intent with implementation evidence."
---

## What it is
A manual test for `scripts/primitive_harness_coverage.py`, which reports, per agentic primitive, whether its declared scope (e.g. `SCOPE: both`) actually has implementation coverage across five distinct surface kinds — `ide-harness`, `cli`, `shell-ci`, `ui`, `report` — instead of collapsing scope and coverage into one misleading claim.

## Key mechanics
- Step 1: regenerate the report via `python3 scripts/primitive_harness_coverage.py --project-dir .`.
- Step 2: load `docs/06-Daily/reports/primitive-harness-coverage-latest.json`, print `summary`, and assert `schema_version == 'primitive-harness-coverage.v1'`, that `surfaces` is present, that all 5 surface kinds are a subset of `surface_kinds`, that `harness_wired_hooks['claude'] >= harness_wired_hooks['codex']`, and that `unclassified_gaps == 0`.
- Step 3: prove CLI JSON/exit-code contracts via `bash scripts/cos status --json`, `bash scripts/cos coverage --json`, and `bash scripts/cos primitive harness-coverage --print-json`, each validated with `python3 -m json.tool`.
- Step 4: inspect concrete rows for 7 named primitives (e.g. `hooks/session-init.sh`, `rules/RULES-COMPACT.md`, `scripts/cos-status.sh`) printing `scope`, `coverage`, `gap`, and specific surface entries (`cos-cli`, `dashboard`).
- Step 5: grep the dashboard codebase (`dashboard/lib`, `dashboard/app`) for references to the report file, the phrase "Primitive Surface Coverage," and "observe-only" — confirming the dashboard consumes the report without mutating it.
- Step 6: run `tests/unit/test_primitive_harness_coverage.py`, `tests/contracts/test_primitive_harness_coverage_contract.py`, `tests/contracts/test_cos_cli_surface_contract.py`.
- Explicit non-claims: does not prove every future IDE has native lifecycle support and does not claim a TUI exists — the report's design allows adding a TUI later as a real `ui` surface without restructuring.

## Relations & where used
Depends on `scripts/primitive_harness_coverage.py`, `scripts/cos` CLI (`status`, `coverage`, `primitive harness-coverage` subcommands), and the `dashboard/` consumer. Sibling to `primitive-duplication-audit.md` and `primitive-readiness-ledger.md` in the same primitive-audit family feeding ACC.

## Status / caveats
No dated snapshot. The `harness_wired_hooks['claude'] >= harness_wired_hooks['codex']` assertion encodes a current-state ordering assumption (Claude has equal-or-more wired hooks than Codex) — worth flagging as a coupling point that would need updating if Codex coverage ever surpasses Claude's.
