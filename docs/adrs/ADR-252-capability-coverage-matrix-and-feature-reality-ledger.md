---
adr: 252
title: Capability Coverage Matrix and Feature Reality Ledger
status: accepted
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
