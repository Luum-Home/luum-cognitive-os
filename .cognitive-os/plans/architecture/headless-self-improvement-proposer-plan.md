---
related-adr: ADR-134
---

<!--
RECONCILIATION STATUS: NEAR-COMPLETE — 2026-05-10 (post-v0.28.0)
Reconciled-by: P2 plan reconciliation (see docs/06-Daily/reports/p2-plan-reconciliation-2026-05-10.md)
Status:
- Phase 1 (Proposal loop): DONE (all 7 items already checked).
- Phase 2 (Doctrine proposer): DONE (all 4 items already checked).
- Phase 3 (Consumer evidence import/export): DONE (all 8 items already checked); reinforced post-v0.28.0 by consumer fleet status panel (commit 2dd2e0144) and consumer-leakage cleanup (39ce28fb4).
- Phase 4 (Background proposer): MOSTLY DONE — scheduled propose-only runner, non-zero reliability stop, and human-approved promotion are proven; automatic branch/PR creation remains split/deferred because current doctrine is propose-only artifact plus human-approved promotion.
Recommendation: keep ACTIVE only for the branch/PR auto-creation decision, or split that item into a separate opt-in PR proposer ADR before archiving this plan.

OPUS REFINEMENT — 2026-05-11 (post-v0.28.0):
Verified all Phase 1-3 scripts exist on disk: scripts/cos-self-improvement-loop, cos-self-improvement-discipline-gate, cos-doctrine-proposer, cos-export-consumer-evidence, cos-import-consumer-evidence, cos-registry-lock, cos-engram-bundle, cos-engram-import-propose, cos-federation-trigger-audit, cos-cross-instance-drill. .cognitive-os/improvements/proposals/ contains generated proposal artifact (self-improvement-proposals-20260503T045251Z.json). Phase 4 is now mostly closed by the scheduled propose-only runner tests; only the branch/PR auto-creation decision remains open and should stay split/deferred unless an opt-in PR proposer ADR is accepted. Opus AGREES with NEAR-COMPLETE. Recommendation: archive after resolving or splitting that single decision.
-->

# Headless Self-Improvement Proposer Plan

## Goal

Turn existing Cognitive OS audits into bounded fix proposals without requiring a
dashboard and without allowing uncontrolled self-modification.

## Phase 1 — Proposal loop

- [x] Add `lib/self_improvement_loop.py`.
- [x] Add `scripts/cos-self-improvement-loop`.
- [x] Normalize `cos-boring-reliability` warnings.
- [x] Normalize `cos-claim-signature-audit` warnings.
- [x] Persist optional proposal JSON under `.cognitive-os/improvements/proposals/`.
- [x] Cover proposal generation with unit tests.
- [x] Add `scripts/cos-self-improvement-discipline-gate` so generated
      proposals cannot quietly become default-surface expansion.

## Phase 2 — Doctrine proposer

- [x] Add `scripts/cos-doctrine-proposer`.
- [x] Read false-positive, direct-main-bypass, demotion-loop, and tier-claim
      evidence.
- [x] Write proposal markdown under `docs/03-PoCs/proposals/`.
- [x] Require any doctrine amendment to start as proposed with
      `runtime_effect: none`, never default-on.

## Phase 3 — Consumer evidence import/export

- [x] Add `scripts/cos-export-consumer-evidence`.
- [x] Add `scripts/cos-import-consumer-evidence`.
- [x] Feed qualifying reports into `manifests/external-adoption-evidence.yaml`.
- [x] Keep non-maintainer 30-day evidence as the threshold for signing the
      helps-projects claim.
- [x] Add registry locks with `scripts/cos-registry-lock`.
- [x] Add propose-only Engram bundles with `scripts/cos-engram-bundle` and
      `scripts/cos-engram-import-propose`.
- [x] Add Shape-B trigger audit with `scripts/cos-federation-trigger-audit`.
- [x] Add manual drills with `scripts/cos-cross-instance-drill` to provoke
      external-evidence, Shape-B trigger, registry-drift, Engram-conflict, and
      governance-checklist states without mutating real evidence.

## Phase 4 — Background proposer

- [x] Add a scheduled propose-only runner. (verified: .venv/bin/python -m pytest tests/unit/test_self_improvement_runner.py -q)
- [x] Ensure the runner stops on non-zero `cos-boring-reliability`. (verified: .venv/bin/python -m pytest tests/unit/test_self_improvement_runner.py -q)
- [x] Decide whether branch/PR creation remains desired; current doctrine is propose-only artifact + human-approved promotion, so auto branch/PR should stay split/deferred unless an opt-in PR proposer ADR is accepted. (closed: closed as rejected-by-current-doctrine: auto branch/PR remains opt-in future ADR, not default requirement; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
- [x] Keep merge/promotion human-approved. (verified: .venv/bin/python -m pytest tests/unit/test_self_improvement_runner.py -q)

## Non-goals

- No dashboard in this phase.
- No auto-merge.
- No auto-promotion to `core` or `team`.
- No fabricated ROI evidence.
- No federation work unless ADR-132 Shape-B triggers fire.

## Validation

```bash
python3 -m pytest tests/unit/test_self_improvement_loop.py -q
python3 -m pytest tests/unit/test_self_improvement_discipline_gate.py -q
scripts/cos-self-improvement-loop --profile core --json
scripts/cos-self-improvement-discipline-gate --profile core --json
```
