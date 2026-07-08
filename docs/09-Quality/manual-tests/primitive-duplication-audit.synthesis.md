---
type: quality-synthesis
source: docs/09-Quality/manual-tests/primitive-duplication-audit.md
provenance: "Manual test verifying the primitive duplication audit runs locally, emits JSON/Markdown reports, and produces actionable common-home recommendations for consolidating duplicated agentic primitives."
---

## What it is
A short manual test confirming `scripts/primitive_duplication_audit.py` produces schema-versioned, ACC-integrated duplication findings, plus a triage protocol for how those findings should be classified rather than auto-acted on.

## Key mechanics
- Run: `python3 scripts/primitive_duplication_audit.py --project-root . --json`, then a Python snippet loads `docs/06-Daily/reports/primitive-duplication-latest.json`, prints its `summary`, and asserts `schema_version == 'primitive-duplication-audit.v1'` and that `findings` is present in the summary.
- Also runs `scripts/acc_pipeline.py --project-dir . --refresh --brief | python3 -m json.tool | grep primitive_duplication` to confirm the ACC refresh includes the `primitive_duplication` adapter.
- Expected result: both JSON and Markdown reports exist at `docs/06-Daily/reports/primitive-duplication-latest.{json,md}`; findings include `recommendation`, `common_home`, and `consumer_relevance` fields; the ACC refresh output includes the adapter.
- Triage notes (the operative governance content): findings must NOT be auto-extracted; each top candidate must be manually classified as one of extract now / intentional duplication / needs owner review / false positive / blocked by harness/projection semantics.

## Relations & where used
Depends on `scripts/primitive_duplication_audit.py` and `scripts/acc_pipeline.py`. Sibling reports live alongside `primitive-harness-coverage.md` and `primitive-readiness-ledger.md` under the same `docs/06-Daily/reports/` primitive-audit family, all feeding into the ACC pipeline.

## Status / caveats
Short, focused test with no dated snapshot or planned/future scaffolding. The triage-classification list is a governance guardrail — it explicitly warns against over-automating consolidation from raw findings.
