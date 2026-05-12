---
adr: 254
title: External Tool Intelligence Plane and Project Overlays
status: accepted
implementation_status: partial
date: '2026-05-08'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
partial_remaining: quarantined by a follow-up cleanup plan.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-254 — External Tool Intelligence Plane and Project Overlays

status: accepted

## Status
Accepted

<!-- SCOPE: OS -->

**Status**: Accepted
**Date**: 2026-05-08

## Context

The external-tools radar grew from one-off scouting into a broad repository
corpus: radar reports, adoption doctrine, adapter taxonomy, dependency manifests,
SBOM-style inventories, and project-consumer concerns. A consumer project should
not need to replicate COS-level deep research every time it evaluates a local
tool. That would duplicate work, create conflicting verdicts, and make adoption
truth harder to prove.

ADR-253 is already reserved as the squads tombstone, so this decision uses the
next available slot.

## Decision

Create an **External Tool Intelligence Plane** with three layers:

| Layer | Owner | Content |
|---|---|---|
| Research base | COS | Deep research, doctrine, external comparisons, benchmarks |
| Adoption manifest | COS | Machine-readable verdict, status, evidence, constraints |
| Project overlay | Consumer project | Real usage, local constraints, receipts, exceptions |

The OS repository owns reusable external-tool intelligence. Consumer projects
own only lightweight overlays that declare local use, local constraints,
receipts, and explicit overrides.

## Implementation

This ADR lands the first complete slice:

- `manifests/external-tools-adoption.yaml` — central external-tool adoption
  ledger.
- `templates/external-tools-overlay.yaml` — consumer-project overlay template.
- `scripts/cos-tool-inventory` — repository-derived external tool inventory.
- `scripts/cos-tool-adoption-audit` — joins manifest, dependencies, and project
  overlay to find contradictions.
- `scripts/cos-tool-radar-render` — renders OS-only, project-only, and combined
  radar views.
- `scripts/cos-tool-research-check` — validates new-tool research packets before
  dependencies or public claims are added.
- `docs/06-Daily/reports/external-tools-deep-dive/` — deep-dive location for tools that
  move past candidate/pilot/adopt thresholds.

## Rules

1. If a tool exists in the COS adoption manifest, a consumer project references
   it and adds local evidence rather than recreating deep research.
2. If a tool is project-only, the project may keep it local or propose promotion
   into the COS manifest when it becomes reusable.
3. If a project contradicts the COS verdict, it must provide a waiver with owner,
   reason, expiry, and evidence.
4. `ADOPT` or `INTEGRATE` entries require consumer proof before public claims.
5. `REMOVE` entries must not remain in direct dependency files unless explicitly
   quarantined by a follow-up cleanup plan.
6. Runtime dependency additions require license, footprint, adoption kind, source
   links, test plan, and rollback path.

## Consequences

- COS avoids reinventing third-party research per consumer project.
- Consumer projects still preserve local autonomy through overlays and waivers.
- Tool adoption becomes auditable by scripts instead of scattered prose only.
- Future adoption decisions can reuse existing control-plane primitives:
  adoption truth, capability coverage, public-claim gates, and dependency gates.

## Alternatives rejected

| Alternative | Rejection rationale |
|---|---|
| Let every consumer project maintain its own deep external-tool radar | Rejected because it duplicates COS research, produces conflicting verdicts, and makes adoption truth harder to audit. |
| Put consumer-specific usage decisions directly into the COS adoption manifest | Rejected because local constraints, receipts, and waivers belong in project overlays, not in reusable OS-level intelligence. |
| Keep the radar as prose-only reports | Rejected because scripts need a machine-readable adoption ledger to detect contradictions and stale claims. |

## Verification

```bash
python3 -m pytest tests/unit/test_external_tool_intelligence.py -q
python3 -m pytest tests/behavior/test_external_tool_intelligence_cli.py -q
scripts/cos-tool-adoption-audit --json
scripts/cos-tool-radar-render --mode combined --json
```
