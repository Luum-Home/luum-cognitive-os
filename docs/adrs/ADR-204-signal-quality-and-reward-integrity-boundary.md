---
adr: 204
title: Signal Quality and Reward Integrity Boundary
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

# ADR-204 — Signal Quality and Reward Integrity Boundary

## Status
Accepted — implemented


<!-- SCOPE: OS -->

**Status**: Accepted — implemented  
**Date**: 2026-05-06  
**Related**: ADR-031, ADR-083, ADR-134, ADR-135, ADR-188, ADR-201  
**Source**: `.cognitive-os/strategy/research/01-origin-archeology.md`, `.cognitive-os/strategy/research/07-skill-ecosystem-evolution.md`, `.cognitive-os/strategy/research/08-self-improvement-roadmap.md`

---

## Context

The self-improvement research found that Cognitive OS' original autonomous loop
broke at the signal-quality boundary. Trust scores can default to `75`,
`skill-feedback.jsonl` can contain identity-corrupted values such as
`skill: matias`, and downstream consequence engines then emit only `maintain`.

ADR-201 already requires a performance ledger and signal-quality quarantine. This
ADR makes reward integrity a separate boundary: no maintainer, router, skill
rewrite, promotion, demotion, or confidence update may use unvalidated reward
signals.

## Decision

Introduce a **Reward Signal Contract** for all metrics that can influence
policy, routing, promotion, demotion, or maintainer proposals.

A reward signal is valid only if it declares:

- source stream;
- schema version;
- subject id and subject type;
- actor/harness/session ids;
- outcome type;
- evidence reference;
- confidence source;
- timestamp;
- validation status.

Rows are classified as `valid`, `suspect`, or `corrupt`. Only `valid` rows may
contribute to scoring. `suspect` and `corrupt` rows are preserved for forensics
and may produce maintainer findings, but cannot drive policy changes.

## Minimal invalid cases

- default trust score with no evidence source;
- `skill` field that is not a known skill id;
- operator/person names in skill identity fields;
- impossible success/cost/latency values;
- missing session/audit/change id when the source stream claims correlation;
- parseable row with unknown schema version.

## Consequences

### Positive

- Maintainer proposals cannot optimize against garbage input.
- Router confidence and skill lifecycle changes become evidence-backed.
- Data-quality failures become first-class findings instead of silent poison.

### Negative / trade-offs

- Early ledger rollups may quarantine large portions of existing metrics.
- More writers need schema discipline.
- Some historical metrics become forensic-only.

## Implementation slices

1. Add `manifests/reward-signal-contract.yaml` with known reward streams and
   required fields.
2. Add `lib/reward_signal_quality.py` and `scripts/cos-reward-signal-audit`.
3. Validate trust-score and skill-feedback rows before ADR-201 ledger rollups.
4. Emit quality counts into performance-ledger summaries.
5. Block `PromoteFromTelemetry` from consuming streams with corrupt ratio above
   policy threshold.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_reward_signal_quality.py -q
scripts/cos-reward-signal-audit --json
```

The tests must prove default trust scores and `skill: matias` rows are
quarantined and cannot affect rollups.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
