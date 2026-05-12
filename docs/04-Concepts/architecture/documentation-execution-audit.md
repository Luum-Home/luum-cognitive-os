# Documentation Execution Audit

## Purpose

Classify documentation items as done, planned, proposed, stale, or missing proof by comparing docs against local repo evidence.

## Command

```bash
python3 scripts/docs_execution_audit.py \
  --json-out docs/06-Daily/reports/docs-execution-latest.json \
  --md-out docs/06-Daily/reports/docs-execution-latest.md
```

## Operating Rule

Report-only by default. Do not auto-rewrite documentation until the baseline is triaged.

Decision record: `docs/02-Decisions/adrs/ADR-097-documentation-execution-audit.md`.
