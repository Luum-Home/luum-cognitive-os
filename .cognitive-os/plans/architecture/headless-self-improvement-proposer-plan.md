---
related-adr: ADR-134
---

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
- [x] Write proposal markdown under `docs/proposals/`.
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

## Phase 4 — Background proposer

- [ ] Add a scheduled propose-only runner.
- [ ] Ensure the runner stops on non-zero `cos-boring-reliability`.
- [ ] Ensure the runner opens a branch/PR only after tests pass.
- [ ] Keep merge/promotion human-approved.

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
