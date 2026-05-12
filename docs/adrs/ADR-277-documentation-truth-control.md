---
adr: 277
title: Documentation Truth Control
status: accepted
implementation_status: implemented
classification_basis: 'Manifest, auditor, generated blocks, reports, ACC adapter, and contract tests are implemented for declared volatile documentation claims.'
date: 2026-05-12
supersedes: []
superseded_by: null
extends: [ADR-146, ADR-256, ADR-276]
implementation_files:
  - manifests/documentation-truth-claims.yaml
  - scripts/documentation_truth_audit.py
  - scripts/cos-documentation-truth-audit
  - docs/architecture/documentation-truth-control.md
  - docs/reports/documentation-truth-latest.json
  - docs/reports/documentation-truth-latest.md
  - tests/contracts/test_documentation_truth_audit.py
  - tests/unit/test_documentation_truth_audit.py
  - tests/unit/test_acc_documentation_truth_adapter.py
tier: maintainer
tags: [documentation, truth, drift, acc, generated-reports]
---
# ADR-277: Documentation Truth Control

## Status

Accepted and implemented.

## Context

Cognitive OS already uses generated reports for primitive readiness, projection fidelity, authority/write-effects, docs execution, and ACC. Those reports are more current than manually authored prose, but Markdown can still drift. Recent examples include docs that described projection proof as Claude/Codex-only after structural harness projection existed, and authority docs that first described write-effects audit as a gap before ADR-276 implemented it.

A generic Markdown linter cannot solve this class of problem. The issue is whether a volatile claim is backed by the current report, and whether the doc has stale contradictory language.

## Decision

Introduce `manifests/documentation-truth-claims.yaml` as the canonical registry of volatile documentation claims.

Each claim declares:

- source reports/manifests;
- required docs;
- required phrases;
- forbidden stale phrases;
- generated truth block placement.

Add `scripts/documentation_truth_audit.py` and `scripts/cos-documentation-truth-audit` to audit those claims and produce:

- `docs/reports/documentation-truth-latest.json`
- `docs/reports/documentation-truth-latest.md`

Add generated truth blocks to docs where facts should be report-derived instead of hand-maintained.

Wire the output into ACC as adapter `documentation_truth` so stale or contradictory docs become capability coverage debt.

## Consequences

- Documentation currentness becomes a contract rather than an informal review task.
- Claims are exhaustive for declared volatile families and ratchet forward as new drift classes are discovered.
- The system avoids pretending to understand all free prose. It blocks declared contradictions and stale generated blocks.
- Writers must update the manifest when adding a volatile factual claim that depends on generated reports.

## Operational Guide

### What changes for the operator

| Surface | Before ADR-277 | After ADR-277 |
|---|---|---|
| Volatile prose claims | maintained by hand, drift detected ad-hoc in review | declared in `manifests/documentation-truth-claims.yaml`, audited each run |
| Stale phrases | discovered when a reader catches them | flagged as findings in `docs/reports/documentation-truth-latest.{json,md}` |
| Generated truth blocks | optional convention | required at declared anchor; auditor enforces block presence + freshness |
| ACC capability coverage | independent of doc currentness | `documentation_truth` adapter feeds claim results into ACC; stale docs lower capability classification |

### Daily operational pattern

1. Author adds a volatile factual claim to a markdown doc.
2. Author registers it in `manifests/documentation-truth-claims.yaml` with source reports, required phrases, forbidden stale phrases, and the generated-truth-block anchor.
3. Run the audit:
   ```bash
   python3 scripts/documentation_truth_audit.py --project-dir . --json --fail-on-block
   ```
   (or via `scripts/cos-documentation-truth-audit`).
4. The audit refreshes `docs/reports/documentation-truth-latest.{json,md}` and writes any declared generated truth blocks.
5. Stale or contradictory claims surface in ACC via the `documentation_truth` adapter on the next ACC run.

### Reading guide for cold readers

1. Open `manifests/documentation-truth-claims.yaml` to see which claims are tracked.
2. Read `docs/architecture/documentation-truth-control.md` for the design + extension protocol.
3. Read `docs/reports/documentation-truth-latest.md` for current claim health.
4. Run the audit in `--json` mode to inspect machine findings (`severity`, `code`, `claim_id`, `surface`).
5. Contract tests at `tests/contracts/test_documentation_truth_audit.py` show valid claim shapes.

The system is claim-driven, not free-prose-driven: only claims declared in the manifest are enforced. Adding new volatile families is the operator's job when drift is observed.

## Verification

The implementation is validated by:

- `tests/contracts/test_documentation_truth_audit.py`
- `tests/unit/test_documentation_truth_audit.py`
- `tests/unit/test_acc_documentation_truth_adapter.py`
- `python3 scripts/documentation_truth_audit.py --project-dir . --json --fail-on-block`
- ACC loading adapter `documentation_truth`

```bash
# Verify ADR-277 implementation files exist
ls -la manifests/documentation-truth-claims.yaml
ls -la scripts/documentation_truth_audit.py
ls -la scripts/cos-documentation-truth-audit
ls -la docs/architecture/documentation-truth-control.md
ls -la docs/reports/documentation-truth-latest.json
ls -la docs/reports/documentation-truth-latest.md
ls -la tests/contracts/test_documentation_truth_audit.py
ls -la tests/unit/test_documentation_truth_audit.py
```

