# Audit/Contract Lane Recovery Plan

## Status

Implemented and tracked by ADR-103.

## Goal

Recover the audit/contract validation lane without hiding deterministic docs debt
or turning broad test failures into startup/session overhead.

## Scope

- Keep audit and contract checks explicit in CI/local validation.
- Fix deterministic documentation debt before broad parallel repair work.
- Preserve focused checks for agentic primitive coverage, docs execution claims,
  and contract behavior.

## Verification Paths

- `docs/adrs/ADR-103-audit-contract-lane-recovery.md`
- `scripts/docs_execution_audit.py --project-dir . --fail-hard-gaps`
- `scripts/primitive_coverage.py --project-dir . --adapter cognitive-os --format json --fail-actionable-gaps`
- `python3 -m pytest tests/unit/test_primitive_coverage.py tests/unit/test_primitive_gap_snapshot.py tests/unit/test_primitive_row_audit.py -q`

## Recovery Checklist

- [x] Keep deterministic docs debt visible through `docs_execution_audit.py`.
- [x] Keep primitive/actionable gaps visible through primitive coverage and gap snapshots.
- [x] Keep broad suite repair separate from SessionStart hooks.
- [x] Require explicit proof links for future completion claims.

## Notes

This plan intentionally lives under `.cognitive-os/plans/architecture/` because
`docs/business/master-plan-checklist.md` links to plan artifacts from that
location. If the plan is moved later, update the checklist in the same commit.
