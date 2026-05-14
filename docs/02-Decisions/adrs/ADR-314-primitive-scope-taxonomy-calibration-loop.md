---
adr: 314
title: Primitive Scope Taxonomy Calibration Loop
status: accepted
implementation_status: implemented
date: '2026-05-14'
extends:
  - ADR-019
  - ADR-146
  - ADR-151
  - ADR-306
supersedes: []
superseded_by: null
implementation_files:
  - scripts/primitive_scope_classifier.py
  - scripts/primitive_scope_unknown_triage.py
  - tests/unit/test_primitive_scope_classifier.py
  - tests/unit/test_primitive_scope_unknown_triage.py
  - docs/04-Concepts/architecture/primitive-scope-classification.md
  - docs/06-Daily/reports/primitive-scope-classifier-iteration-control-2026-05-14.md
  - docs/06-Daily/reports/primitive-scope-classifier-iteration-001-both-review-2026-05-14.md
  - docs/06-Daily/reports/primitive-scope-classifier-manual-review-2026-05-14.md
tier: maintainer
tags:
  - scope
  - taxonomy
  - primitive-governance
  - portability
  - calibration
classification_basis: accepted and implemented after reviewing the reverted scope-reclassification commits a239dcff and 33682e2e; the implementation creates an evidence-weighted classifier plus an auditable iteration-control loop so future scope changes are hypotheses reviewed in bounded batches, not grep-only bulk rewrites.
verification:
  level: high
  commands:
    - .venv/bin/python -m pytest tests/unit/test_primitive_scope_classifier.py tests/red_team/portability/test_cos_init.py tests/contracts/test_primitive_scope_classification.py tests/unit/test_primitive_scope_governance.py tests/unit/test_scope_both_portability_audit.py -q
    - .venv/bin/python scripts/primitive_scope_classifier.py --project-dir . --paths scripts/primitive_scope_classifier.py --fail-contradictions
  proves:
    - classifier distinguishes suggested_scope from safe effective_scope
    - package skills touched by 33682e2e are included in classifier inventory
    - scoped gate can be run on explicit primitive paths without full-repo churn
    - both-positive review is recorded as an iteration artifact instead of marker rewrites
---

# ADR-314 — Primitive Scope Taxonomy Calibration Loop

## Status

Accepted and implemented — 2026-05-14.

<!-- SCOPE: OS -->

## Context

ADR-019 introduced the `os-only` / `project` / `both` taxonomy so OS-internal
agentic primitives would not leak into consumer projects. ADR-306 later added a
runtime projection audit so scope markers are checked against source and
consumer-install behavior.

Those controls still left a dangerous gap: **the process for changing the
classification itself was not governed**. A future agent could read many files,
see OS-internal words such as `.cognitive-os/`, `manifests/`, `docs/02-Decisions/`,
or `scripts/cos-*`, and bulk-rewrite `SCOPE: both` to `SCOPE: os-only` while
believing the rewrite was evidence-based.

This failure happened in two recent commits:

- `a239dcff refactor(scope): reclassify SCOPE: both → os-only across hooks and skills`
- `33682e2e refactor(scope): deep content audit — 24 more skills reclassified os-only`

Both commits were later reverted (`c646d17b` and `9b5f66ce`). Re-review showed
that the mistake was not merely one bad list of files. The root issue was an
ungoverned classification workflow:

1. source-repo path mentions were treated as distribution proof;
2. `both` was treated as suspicious by default;
3. insufficient evidence was conflated with final `os-only` classification;
4. package skills changed by `33682e2e` were not covered by the first classifier
   inventory until this ADR's implementation added package-skill scanning;
5. full-repo output could be mistaken for an instruction to mass-edit markers.

The taxonomy must support all three real outcomes, with semantic meaning before metadata scoring:

- `os-only` — primitives whose principles, procedures, or implementation are only required to construct, validate, explain, or operate Cognitive OS itself. Strong signals include Cognitive OS-specific internals, manifests, ADR meshes, docs paths, or scripts that downstream projects will not contain.
- `project` — primitives that affect downstream projects only, and that Cognitive OS does not need to contemplate as part of constructing or validating itself.
- `both` — agnostic repository-construction guidance usable in Cognitive OS and in any downstream repository.

A safe system must also represent **unknown** during calibration. Unknown is not
a fourth persisted `SCOPE` marker; it is a classifier finding meaning evidence is
insufficient. Unknown rows use `effective_scope=os-only` only as a safe projection
fallback until metadata/proof exists.

## Decision

Adopt an evidence-weighted **Primitive Scope Taxonomy Calibration Loop**.

The loop has two parts:

1. `scripts/primitive_scope_classifier.py` — a classifier that emits row-level
   hypotheses from durable evidence.
2. `docs/06-Daily/reports/primitive-scope-classifier-iteration-control-*.md` —
   an auditable iteration ledger controlling manual review and changes.

The classifier must emit both:

- `suggested_scope` — the evidence-derived taxonomy hypothesis: `os-only`,
  `project`, `both`, or `unknown`;
- `effective_scope` — the safe operational fallback used by gates/projection.
  `unknown` maps to `effective_scope=os-only` until proven otherwise.

The classifier must use distribution/projection evidence, not grep-only source
mentions. Unknown rows then flow through `scripts/primitive_scope_unknown_triage.py`, which groups missing evidence and deterministic semantic hints before any manual or AI-assisted adjudication.

Current evidence sources are:

- `manifests/primitive-scope-overrides.yaml` as fallback metadata for legacy
  paths without explicit headers;
- `manifests/primitive-readiness-protected-install-surfaces.yaml` only for direct
  projection/application surfaces (`bootstrap`, `settings-projection`,
  `profile-application`), not every protected maintainer script;
- `manifests/primitive-consumer-availability.yaml`;
- `manifests/primitive-lifecycle.yaml`;
- paired portability/falsification proof paths, as a proof gate for `both`, not
  as standalone distribution evidence.

The classifier inventory must include the primitive families affected by the
bad commits:

- root hooks;
- root skills;
- package skills under `packages/*/skills/*/SKILL.md`;
- rules;
- scripts;
- templates.

No full-repo classifier run may directly drive marker rewrites. Full runs create
backlog. Enforcement gates must use explicit changed/staged paths through
`--paths` or a similarly bounded input.

## Commit re-review findings

Re-review of `a239dcff` under the current classifier showed that the commit's
bulk change was mixed, not uniformly correct:

```text
files changed: 156
classified by current classifier: 155
current suggested_scope among classified files:
  both: 18
  os-only: 76
  unknown: 61
```

This means a blanket `both → os-only` rewrite would still be wrong: at least 18
rows currently have positive `both` evidence, and 61 rows remain unknown rather
than proven `os-only`.

Re-review of `33682e2e` showed why package-skill coverage matters:

```text
files changed: 26
classified by current classifier: 24
current suggested_scope among classified files:
  os-only: 3
  unknown: 21
```

Most of the package/root skills from that commit are not proven `os-only`; they
are missing enough evidence to decide. They should become metadata/proof work
items, not automatic demotions.

## Iteration protocol

Every calibration pass must follow this sequence:

1. run the classifier;
2. choose one bucket;
3. write the hypothesis;
4. manually review rows or a bounded representative set;
5. decide whether the classifier, metadata, proof, or marker is wrong;
6. make one class of change;
7. run targeted tests;
8. record the iteration result before moving on.

The iteration-control artifact owns the current state machine, stop conditions,
and backlog order. Iteration 1 reviewed `suggested_scope=both` and split 65 rows
into:

- 48 confirmed `both` rows;
- 14 candidate rows with marker/proof gaps;
- 3 rows with exact `both` fallback overrides but missing explicit headers.

No marker changes were made in Iteration 1.

## Consequences

### Positive

- Scope changes become auditable hypotheses instead of bulk edits.
- `unknown` prevents insufficient evidence from being mislabeled as final
  `os-only`.
- `both` remains a valid, expected outcome when distribution evidence and proof
  exist.
- Package skills are now part of the classifier inventory, closing the gap found
  by re-reviewing `33682e2e`.
- Future agents can continue the loop from explicit iteration artifacts.

### Negative / trade-offs

- Full-repo counts are not a quick pass/fail answer; they create review backlog.
- Some rows need metadata/proof work before classification can be resolved.
- `project` still needs a stronger positive evidence model and must not be
  collapsed into `both` or `os-only` without consumer-project-only proof.
- The classifier will require calibration as lifecycle and consumer-availability
  semantics improve.

## Alternatives rejected

- **Keep ADR-306 only.** Rejected because ADR-306 proves projection/runtime
  behavior for existing markers; it does not govern how markers should be
  changed when evidence is incomplete or contradictory.
- **Mass-reapply the reverted commits after manual inspection.** Rejected because
  current evidence shows mixed outcomes across the touched files.
- **Treat missing evidence as final `os-only`.** Rejected because that recreates
  the same bias under a more formal name. Missing evidence is `unknown` with a
  safe operational fallback.
- **Let paired portability proof infer `both`.** Rejected because proof is
  necessary but not sufficient; distribution intent must come from lifecycle,
  consumer availability, projection, or exact fallback metadata.

## Verification

```bash
.venv/bin/python -m pytest tests/unit/test_primitive_scope_classifier.py tests/red_team/portability/test_cos_init.py tests/contracts/test_primitive_scope_classification.py tests/unit/test_primitive_scope_governance.py tests/unit/test_scope_both_portability_audit.py -q
.venv/bin/python scripts/primitive_scope_classifier.py --project-dir . --paths scripts/primitive_scope_classifier.py --fail-contradictions
```
