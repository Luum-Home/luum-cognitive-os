---
type: quality-synthesis
source: docs/09-Quality/manual-tests/closure-discipline.md
provenance: "Manual test proving a multi-file maintainer batch didn't just pass feature-local tests but also closed every validation surface it invalidated, before it can be called done."
---

## What it is
A procedure and decision framework for verifying "closure discipline" — that a maintainer batch touching CI/hook/validation-surface files re-validates every downstream contract it could have broken, rather than stopping at feature-local green tests.

## Key mechanics
- Trigger conditions: run before calling a batch done if it touches `.github/workflows/` or ADR-130/131 local-CI migration files; hook projection, `.claude/settings.json`, `.codex/hooks.json`, or `manifests/primitive-lifecycle.yaml`; validation capsules, worktree cleanup, WIP inventory, or broad validation lanes; tests asserting repo-wide counts/generated artifacts/preserved disabled files; or ADRs claiming a new gate/lifecycle state/validation contract.
- Procedure: (1) `scripts/cos-closure-discipline-audit --fail-on-findings --json` must be green; (2) re-run a fixed regression set for known closure-drift classes (`test_closure_discipline_audit.py`, `test_test_lanes_workflow.py`, `test_primitive_gap_workflow.py`, `test_primitive_coverage.py`, `TestCollectWorktreesDirect`, `test_repository_settings_hook_count_is_report_derived_not_hardcoded`, `test_validation_capsule_runs_in_isolated_worktree`); (3) `scripts/primitive_lifecycle.py --json` must show `"valid": true, "finding_count": 0`; (4) `scripts/cos-ci-local.sh quick` must pass; (5) for uncommitted WIP closure, run `make test-laptop-direct`; (6) after committing, run `make test-laptop` (the isolated capsule lane) for release-safe closure — the capsule validates HEAD, not uncommitted edits.
- Pass criteria: closure audit exits 0 with `status: pass`; targeted regression tests pass; primitive lifecycle JSON reports zero findings; quick CI includes and passes the closure-discipline-audit step; any skipped broad/release lane is explicitly named with reason and risk in the final trust report.
- Failure handling triage table: Stale validator/test → update the validator/test and add a closure-audit fixture if the class can recur; Real product regression → fix the behavior and add/repair the feature test; Ambiguous → leave the batch unclosed and write an escalation with the failing command and evidence.
- Explicit rule: a closure claim without this evidence is a partial-completion claim, not a done claim — and if either broad lane fails, release-safe closure cannot be claimed.

## Relations & where used
Drives `scripts/cos-closure-discipline-audit`, `scripts/primitive_lifecycle.py`, `scripts/cos-ci-local.sh`, `make test-laptop-direct`/`make test-laptop`, and the 7 named regression tests. Complements the ADR-130/131 local-CI migration and `manifests/primitive-lifecycle.yaml`.

## Status / caveats
Procedural manual-test document defining a repeatable discipline gate, not a dated execution report — no specific run's results are recorded here.
