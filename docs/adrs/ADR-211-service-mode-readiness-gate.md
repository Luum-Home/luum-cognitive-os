---
adr: 211
title: Service-Mode Readiness Gate
status: accepted
implementation_status: partial
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted/implemented text with explicit partial/deferred scope
---

# ADR-211 — Service-Mode Readiness Gate

## Status
Accepted — initial readiness gate implemented


<!-- SCOPE: OS -->

**Status**: Accepted — initial readiness gate implemented  
**Date**: 2026-05-06  
**Related**: ADR-193, ADR-194, ADR-196, ADR-198, ADR-201, ADR-202, ADR-204, ADR-205, ADR-209  
**Source**: `.cognitive-os/strategy/research/08-self-improvement-roadmap.md`, `.cognitive-os/strategy/02-pre-launch-playbook.md`

---

## Context

The strategy research produced a service-mode readiness ladder for `cosd` and
hosted/cloud operation. Several pieces are individually documented, but no single
gate says when the system is safe to present as standalone service behavior.

## Decision

Add a **Service-Mode Readiness Gate** for any launch claim that Cognitive OS can
run as an autonomous/headless/cloud service.

The gate requires these levels:

1. private-content skeleton manifest and secret boundary;
2. run flight recorder / trace joiner;
3. performance ledger with signal-quality gate;
4. minimum reward signals;
5. maintainer propose-only loop end-to-end;
6. experiment contract for executable changes;
7. service-mode mutation authorization boundary;
8. cloud/private-content leakage smoke;
9. public claim gate passes.

No public service-mode claim may ship while any level is red.

## Consequences

### Positive

- Converts research roadmap into a launch gate.
- Prevents overclaiming service autonomy.
- Aligns ADR-201 and ADR-202 with release readiness.

### Negative / trade-offs

- Delays service/cloud messaging until substrate is real.
- Requires maintaining gate status as ADRs evolve.

## Implementation slices

1. Add `scripts/cos-service-readiness-gate`.
2. Aggregate statuses from ADR-202 audit, ADR-205 trace, ADR-201 ledger,
   ADR-204 reward quality, ADR-209 experiments, ADR-206 claim gate.
3. Add JSON and compact human output.
4. Wire into pre-launch release checklist.
5. Add proof drill for headless service mode.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_service_mode_readiness_gate.py -q
scripts/cos-service-readiness-gate --json
```

The gate must fail if private-content classification, trace joiner, performance
ledger, or public claim evidence is missing.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
