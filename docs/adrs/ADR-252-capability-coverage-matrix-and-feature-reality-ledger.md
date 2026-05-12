---

adr: 252
title: Capability Coverage Matrix and Feature Reality Ledger
status: accepted
implementation_status: partial
classification_basis: 'Slice A establishes the matrix for ADR-230+; historical COS feature classification remains intentionally incomplete'
relationship_chain_exempt: true
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-031, ADR-147, ADR-217, ADR-248, ADR-249, ADR-250, ADR-251]
implementation_files:
  - manifests/capability-coverage.yaml
  - scripts/cos-capability-matrix
  - docs/capabilities/MATRIX.md
  - docs/reports/capability-coverage-latest.json
  - tests/unit/test_capability_matrix.py
tier: maintainer
tags: [capability-coverage, feature-reality, claims, matrix, audit, control-plane]
---

<!-- ADR_RELATION_CHAIN_EXEMPT: part of the 2026-05-08 implementation-ledger ADR burst; relationship depth is tracked by control-plane audits rather than new transitive ADR scope. -->

# ADR-252: Capability Coverage Matrix and Feature Reality Ledger

## Status

Accepted — Slice A implemented.

## Context

The operator asked how to know whether the same gap discovered in ADR-250
(skill-router reinvention) and ADR-251 (orchestration reinvention) exists in
other Cognitive OS capabilities. The recurring problem is not only model
non-determinism. The deeper issue is **source-of-truth fragmentation**:

- ADRs say a capability is accepted;
- manifests declare policy;
- scripts/hooks/skills exist;
- tests prove something, sometimes only structure;
- telemetry or receipts may or may not be emitted;
- docs and public claims may drift ahead of runtime reality.

As a result, a capability can be locally plausible while globally unproven:
script present but unwired, hook present but unregistered, ADR accepted but no
behavioral proof, public claim without a runtime receipt, or benchmark missing
historical failure modes.

Existing ADRs cover slices of the problem:

- ADR-031 audits aspirational/dormant claims;
- ADR-147 tracks agent capability coverage as a broader coverage concept;
- ADR-217 checks adoption truth;
- ADR-248 runs control-plane audits by lane;
- ADR-249 distinguishes behavioral proof from overfit tests;
- ADR-250 and ADR-251 add adapter-boundary benchmarks for router and
  orchestration surfaces.

What is missing is a **single generated matrix** that joins claim → ADR →
implementation → consumer/wiring → tests → receipts → audit → reality level.

## Decision

Introduce a manifest-backed Capability Coverage Matrix and Feature Reality
Ledger.

New artifacts:

```text
manifests/capability-coverage.yaml
scripts/cos-capability-matrix
docs/capabilities/MATRIX.md
docs/reports/capability-coverage-latest.json
tests/unit/test_capability_matrix.py
```

Hard rule:

> If a capability is not in the matrix, it cannot be treated as a public COS
> capability claim.

Every capability declaration must state:

- stable `id`;
- human label;
- owner ADR;
- reality level (`REAL`, `PARTIAL`, `ROADMAP`, `LAB`, `DORMANT`, `DEPRECATED`,
  or `RESOLVED`);
- whether it is a public claim;
- primitive types involved;
- implementation paths;
- consumers/wiring paths;
- tests/evidence paths;
- runtime receipts or metrics;
- control-plane audits that watch it;
- known gaps when reality is not `REAL`.

Slice A covers the ADR-230+ maintainer/control-plane line because that is where
recent gaps appeared. The manifest also declares an ADR coverage range so
accepted ADRs in that range cannot silently disappear from the matrix.

## Reality levels

| Level | Meaning |
|---|---|
| `REAL` | Implemented, wired to a consumer, has tests, and emits or is watched by receipts/audits. |
| `PARTIAL` | Useful substrate exists, but at least one important wiring/proof/coverage gap remains. |
| `ROADMAP` | Deliberate future work. Must not be public-marketed as current behavior. |
| `LAB` | Experimental or opt-in research surface. |
| `DORMANT` | Present but inactive/unwired. |
| `DEPRECATED` | Should not be extended; kept only for compatibility. |
| `RESOLVED` | Incident/follow-up ADR whose work is closed and tracked as evidence, not a live capability. |

## Audit rules

`cos-capability-matrix --json` is read-only by default. It blocks on:

1. accepted ADR in the configured coverage range missing from the matrix;
2. declared implementation/consumer/test path missing;
3. `public_claim: true` with `ROADMAP`, `LAB`, `DORMANT`, or `DEPRECATED`;
4. `REAL` capability without implementation, consumer, test, and receipt/audit
   evidence;
5. non-REAL capability without `known_gaps`;
6. generated matrix/report stale when checked in `--check-generated` mode.

`cos-capability-matrix --write` regenerates:

```text
docs/capabilities/MATRIX.md
docs/reports/capability-coverage-latest.json
```

The write mode is explicit and not used by hook-fast. The control-plane lane
runs the read-only JSON audit.

## Consequences

Positive:

- Makes capability reality visible in one place instead of requiring ad-hoc
  memory of ADRs, tests, scripts, and docs.
- Converts “I wonder what else has this gap” into a stable audit finding.
- Prevents public claims from drifting ahead of implementation evidence.
- Gives future ADRs a predictable place to register themselves.

Negative:

- Adds another manifest that must be maintained when capabilities are added.
- The matrix is only as good as its declared evidence; ADR-249 remains necessary
  to ensure tests are behavioral rather than structural.
- Slice A does not classify every historical COS feature. It establishes the
  contract and covers the recent ADR-230+ control-plane line first.

## Operational Guide

### What changes for the operator

Before this ADR, answering "is capability X actually implemented and wired?"
required reading the ADR (which only says "accepted"), then checking whether
scripts/hooks/skills existed, then checking whether they were wired to consumers,
then checking whether tests existed — with no single place joining all four.

After this ADR:

- `manifests/capability-coverage.yaml` is the single source of truth. Each
  capability entry joins: owner ADR → implementation paths → consumer/wiring
  paths → tests/evidence → runtime receipts → control-plane audits → known gaps.
- The reality level (`REAL`, `PARTIAL`, `ROADMAP`, `LAB`, `DORMANT`,
  `DEPRECATED`, `RESOLVED`) replaces verbal claims. A `REAL` capability must
  have evidence for all four pillars.
- `docs/capabilities/MATRIX.md` is the generated human-readable view. Use it
  for cold-reading current state without scanning dozens of ADRs.
- `docs/reports/capability-coverage-latest.json` is the machine-readable report
  consumed by the control-plane audit.
- **Hard rule:** If a capability is not in the matrix, it cannot be treated as a
  public COS capability claim.

### What this answers (and what it doesn't)

**Answers:**
- "Is capability X actually real or aspirational?" — Read the matrix entry's
  `reality_level`. `ROADMAP`, `LAB`, or `DORMANT` means it is not public-claim
  safe.
- "Which capabilities have wiring or receipt gaps right now?" — Run
  `python3 scripts/cos-capability-matrix --json` and filter findings by
  `public_claim: true` + `reality_level != REAL`.
- "An ADR was accepted last month — why isn't it in the matrix?" — Because it
  was not registered. Add an entry to `manifests/capability-coverage.yaml` with
  the owner ADR and initial reality level.

**Does not answer:**
- Whether the evidence declared in the matrix is behaviorally sufficient. That
  is ADR-249's responsibility (proof quality audit).
- Whether every historical COS feature is classified. Slice A covers the
  ADR-230+ control-plane line. Older capabilities are added incrementally.

### Daily operational pattern

1. When a new ADR lands, register the capability it delivers:
   - Add an entry to `manifests/capability-coverage.yaml` with the ADR number,
     initial `reality_level: PARTIAL` (since it is usually not fully wired yet),
     and known gaps.
2. To refresh the generated matrix and report:
   ```bash
   python3 scripts/cos-capability-matrix --write
   ```
3. To run the read-only audit (used by hook-fast):
   ```bash
   python3 scripts/cos-capability-matrix --json
   python3 scripts/cos-capability-matrix --check-generated --json
   ```
4. Full verification:
   ```bash
   python3 -m pytest tests/unit/test_capability_matrix.py -q
   scripts/cos-control-plane-audit --lane hook-fast --json
   ```

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Maintain a manual spreadsheet | Goes stale immediately and is invisible to hooks/tests. |
| Rely on ADR status alone | “Accepted” does not prove wiring, receipts, tests, or public-claim safety. |
| Rely on test count/coverage only | Tests can overfit to file existence and miss runtime behavior. |
| Only run aspirational audit | ADR-031 is necessary but not enough; we need implementation/consumer/test/receipt joins. |
| Let agents summarize status in prose | Reintroduces the same non-deterministic/verbal closure failure that caused the incidents. |

## Verification

```bash
python3 scripts/cos-capability-matrix --json
python3 scripts/cos-capability-matrix --check-generated --json
python3 -m pytest tests/unit/test_capability_matrix.py -q
scripts/cos-control-plane-audit --lane hook-fast --json
```

Expected current result: capability coverage passes, generated matrix/report are
fresh, and hook-fast includes the capability matrix audit without findings.
