---

adr: 151
title: Consumer Availability Classification Manifest
status: implemented
implementation_status: implemented
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - manifests/primitive-consumer-availability.yaml
  - scripts/acc_pipeline.py
  - tests/unit/test_acc_pipeline.py
  - tests/contracts/test_acc_pipeline_contract.py
tier: maintainer
tags: [acc, consumer-availability, primitive-readiness, projection]
---

# ADR-151: Consumer Availability Classification Manifest

## Status

**Implemented for manifest/classification scope** — 2026-05-04. The consumer availability manifest, ACC adapter, and contract tests named below exist; future script role changes still require manifest maintenance.

## Context

After adding default/full projection proof, ACC still had 49 partial script rows. They all shared the same broad readiness label: `lifecycle-declared-consumer-candidate`. That label is useful during discovery, but too coarse for scoring:

- some scripts are real future consumer CLI candidates and should remain partial until shell/CI projection proof exists;
- some scripts are SO maintainer tools and should not count as consumer-project debt;
- some scripts may need a future package/driver before they can be claimed as projectable.

Without an explicit classification layer, ACC either over-penalizes maintainer-only primitives or risks over-claiming consumer availability.

## Decision

Add `manifests/primitive-consumer-availability.yaml` as the explicit classification manifest for lifecycle-declared consumer candidates not resolved by projection output.

Allowed statuses are:

| Status | ACC meaning |
|---|---|
| `shell-ci-candidate` | Intended consumer CLI/shell surface, but still partial until shell/CI projection proof exists. |
| `projectable-needs-driver` | Intended consumer surface, but no harness/profile driver exists yet. |
| `maintainer-only` | SO maintainer primitive; aligned because it is not consumer-project debt. |
| `so-local-only` | Local helper/context surface; aligned because it is not consumer-project debt. |

ACC loads this manifest through a `consumer_availability` adapter. Rows marked `maintainer-only` or `so-local-only` become aligned with explicit rationale. Rows marked `shell-ci-candidate` or `projectable-needs-driver` remain partial.

## Consequences

### Positive

- Partial weight drops without pretending every script is projected.
- Maintainer-only scripts become explicitly documented rather than hidden in heuristics.
- Remaining partial rows are now higher-signal: they are actual shell/CI or driver candidates.

### Negative

- The manifest must be kept current when scripts change role.
- Misclassification can hide real consumer debt, so every item requires rationale.
- Shell/CI projection remains unimplemented for the remaining candidates.

## Operational Guide

### What changes for the operator

Before this ADR: ACC treated all 49 lifecycle-declared script candidates with the same `lifecycle-declared-consumer-candidate` label, making maintainer-only tools look like unresolved consumer debt.

After this ADR:

- `manifests/primitive-consumer-availability.yaml` is the explicit classification layer. Every entry has an `availability_status` and a human-readable `rationale`.
- Statuses that **reduce** partial weight: `maintainer-only`, `so-local-only` (these become aligned with explicit rationale).
- Statuses that **preserve** partial weight: `shell-ci-candidate`, `projectable-needs-driver` (these remain partial until projection proof exists).
- To see current classifications:
  ```bash
  cat manifests/primitive-consumer-availability.yaml
  python3 scripts/acc_pipeline.py --project-dir . --brief
  ```

### What this answers (and what it doesn't)

**Answers:**
- "Why is this script not counted as consumer debt?" — Check `manifests/primitive-consumer-availability.yaml` for its `availability_status` and `rationale`.
- "Which scripts are genuine future consumer CLI candidates vs. maintainer tools?" — `shell-ci-candidate` entries are real candidates; `maintainer-only` are not.
- "What happens when a script's role changes?" — Update its entry in the manifest with the new status and rationale, then rerun ACC to confirm the weight change.

**Does not answer:**
- "When will `shell-ci-candidate` scripts become fully proven?" — That requires shell/CI projection proof (see ADR-152).
- "Is this classification correct for all future consumer project topologies?" — Classification reflects current COS architecture; review during major structural changes.

### When sources disagree

If ACC reports a script as partial but the operator believes it is a maintainer tool:
1. Check whether the script has an entry in `manifests/primitive-consumer-availability.yaml`. If absent, ACC uses the discovery label (`lifecycle-declared-consumer-candidate`) by default.
2. Add or update the manifest entry with `availability_status: maintainer-only` and a clear `rationale`.
3. Rerun `python3 scripts/acc_pipeline.py --project-dir . --refresh` to confirm the row moves from partial to aligned.

The manifest is the source of truth; discovery labels are a fallback for unclassified primitives only.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Change the readiness ledger heuristic directly | Rejected because discovery labels are still useful; ACC needs a separate proof/classification layer. |
| Mark all candidates as maintainer-only | Rejected because several CLI/test/status commands are plausible consumer-project surfaces. |
| Keep all candidates partial | Rejected because many are clearly SO maintainer tools and distort ACC. |

## Verification

```bash
python3 scripts/acc_pipeline.py --project-dir . --refresh
python3 -m pytest tests/unit/test_acc_pipeline.py tests/contracts/test_acc_pipeline_contract.py -q
python3 -m py_compile scripts/acc_pipeline.py
```

## Implementation Evidence

- `manifests/primitive-consumer-availability.yaml` classifies 49 script candidates with rationale.
- `scripts/acc_pipeline.py` loads the manifest as `consumer_availability` and applies overrides before scoring.
- `tests/unit/test_acc_pipeline.py` proves maintainer-only overrides align rows.
- `tests/contracts/test_acc_pipeline_contract.py` proves the repository manifest is loaded by ACC.
