---
adr: 328
title: Governance ROI Friction-vs-Catch Ratios
status: accepted
implementation_status: implemented
date: '2026-05-20'
supersedes: []
superseded_by: null
implementation_files:
- scripts/cos_governance_roi.py
- scripts/cos-status.sh
- tests/unit/test_cos_governance_roi.py
- tests/behavior/test_cos_status.py
tier: maintainer
classification_basis: Cognitive OS governance only pays when guard friction prevents real work loss, security risk, high-blast-radius mistakes, or multi-agent coordination failure; the system needs explicit reviewed catch evidence and phase-aware blocking thresholds.
tags:
- governance-roi
- friction
- phase-aware
- cos-status
- metrics
---

# ADR-328 — Governance ROI Friction-vs-Catch Ratios

## Status

Accepted. Implemented as an extension of `scripts/cos_governance_roi.py` and surfaced in `scripts/cos-status.sh`.

## Context

Cognitive OS governance is not a neutral benefit in every context. It pays for itself when the work has high blast radius, multiple agents, security sensitivity, release risk, destructive operations, or meaningful risk of silent work loss. For single-file, exploratory, or low-risk single-developer work, the same guards can create more friction than value.

Recent dogfooding exposed both sides:

- Correct governance prevented silent loss around stash safety, dispatch queue collapse, validation locks, and empty agent payloads.
- Governance itself also produced bugs and false friction: stale validation locks, queue stalls without an automatic tick, and shell/JSON corruption.

A raw count of guard blocks is therefore insufficient. The OS must distinguish **block frequency** from **confirmed useful catches** and tune blocking posture by project phase.

## Decision

Add a first-class **friction-vs-catch ratio** to the governance ROI dashboard and expose it in `cos status`.

### Catch ledger

Reviewed guard outcomes are recorded in an append-only JSONL ledger:

```text
.cognitive-os/metrics/governance-catches.jsonl
```

Minimal row shape:

```json
{"ts":"2026-05-20T00:00:00Z","hook":"dispatch-gate","verdict":"confirmed_valid_block","reason":"blocked empty Agent prompt that would have lost operator intent"}
```

Supported verdict families:

- `confirmed_valid_block` — operator verified the block was correct.
- `false_positive_override` — operator verified the block was noisy or wrong.
- `silent_loss_prevented` — the guard prevented hidden loss of work, intent, or state.
- `high_blast_radius_catch` — the guard prevented a high-impact mistake.

`silent_loss_prevented` and `high_blast_radius_catch` count as confirmed useful catches.

### Ratio

The ratio is:

```text
total blocking guard events / confirmed useful catches
```

If no reviewed catches exist, status is `unknown`; the dashboard must ask for ledger entries instead of pretending that all blocks were correct.

Bands:

| Ratio | Status | Meaning |
|---:|---|---|
| `<= 2x` | `paying` | Guard friction is justified by confirmed catches. |
| `> 2x` and `<= 5x` | `watch` | Keep the guard, but review/tune top blockers. |
| `> 5x` | `cut` | Demote, relax, or make high-friction guards advisory outside high-risk phases. |

### Phase-aware policy

Blocking posture is shaped by `cognitive-os.yaml → project.phase`:

| Phase | Policy |
|---|---|
| `reconstruction` | Minimal blocking: destructive git, secrets, credential leaks, and work-loss risks block; style/process friction should be advisory. |
| `stabilization` | Contract-focused blocking: tests, primitive drift, runtime-state loss, and contract failures can block. |
| `production` | Strict release blocking: release, security, migration, public claims, and protected config changes block. |
| `maintenance` | Regression-focused blocking: regressions, security issues, unsafe changes, and data loss block. |

### Status surface

`cos status` now includes a `governance_roi` object in JSON output and a compact pretty line:

```text
Governance ROI: net=-10.27m ratio=unknown unknown catches=0 false+=0 phase=reconstruction/minimal-blocking
```

## Consequences

### Positive

- The OS can measure whether governance is paying for real catches instead of assuming more blocking is safer.
- False positives become visible and reviewable.
- Phase-specific policy prevents always-on friction from dominating exploratory work.
- The dashboard gives the operator a concrete recut signal: `>5x` means cut or demote guards.

### Negative / trade-offs

- The ratio depends on operator-reviewed ledger rows; without review, the status is intentionally `unknown`.
- The initial benefit model remains heuristic and should not be treated as financial accounting.
- Phase policy is coarse; individual guards still need local judgment and tests.

## Verification

```bash
python3 -m py_compile scripts/cos_governance_roi.py
python3 -m pytest tests/unit/test_cos_governance_roi.py tests/behavior/test_cos_status.py -q
scripts/cos governance roi --json
scripts/cos status --json
```
