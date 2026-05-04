# ADR-134 — Headless Self-Improvement Proposer

<!-- SCOPE: OS -->

**Status**: Accepted  
**Date**: 2026-05-03  
**Related**: ADR-083, ADR-120, ADR-126, ADR-132, ADR-133  
**Implementation**: `scripts/cos-self-improvement-loop`

---

## Context

Cognitive OS already audits its own drift:

- `cos-boring-reliability` aggregates operational warnings.
- `cos-demotion-loop-audit` bounds lifecycle-governor debt.
- `cos-claim-signature-audit` keeps product claims falsifiable.
- `cos-false-positive-ledger`, `silent_failure_audit`, and tier-claim audits
  expose governance debt before it becomes theatre.

The missing step is not a dashboard. The missing step is a closed loop between
observed findings and bounded candidate action:

```text
audit -> normalize finding -> propose bounded fix -> validate -> human review
```

Without that loop, the system still depends on the operator noticing warnings
and manually deciding the next hardening commit.

## Decision

Add a headless, propose-only self-improvement primitive:

```bash
scripts/cos-self-improvement-loop --profile core --mode propose
```

The primitive normalizes existing audit findings into reviewable proposals. It
may write proposal JSON under `.cognitive-os/improvements/proposals/` when
called with `--write`.

It may not:

- auto-merge;
- auto-promote primitives to `core` or `team`;
- invent governance ROI evidence;
- delete or demote primitives without a reversible path;
- extend warning budgets silently.

Every proposal declares:

- source audit;
- finding id;
- severity;
- candidate action;
- allowed write paths;
- required tests;
- human approval requirement;
- blocked actions.

The proposal loop is protected by `scripts/cos-self-improvement-discipline-gate`.
That gate fails proposals that:

- open `auto_merge`;
- open `auto_promote_core_or_team`;
- remove the human-approval requirement;
- propose adding or promoting default-visible `core`/`team` surface;
- allow direct writes to live runtime surfaces such as `hooks/`, `rules/`, or
  root `skills/`;
- omit explicit blocked actions such as `invent_roi_evidence`.

## Consequences

### Positive

- Self-improvement becomes actionable without requiring a dashboard.
- Audit warnings can be converted into bounded work items that are ready for
  review.
- The system moves from self-observing to self-proposing while preserving human
  control.
- The product claim becomes more precise: Cognitive OS is
  **self-improving under governed human review**, not autonomous self-modifying
  software.

### Negative / Trade-offs

- The first implementation still requires the operator to choose which proposal
  to execute.
- Proposals can accumulate if they are not reviewed.
- The primitive can surface obvious proposals but cannot decide product strategy.

## Alternatives rejected

- **Dashboard first**: rejected because visualization does not create a control
  loop. The CLI is the primitive; a dashboard can come later.
- **Auto-fix and auto-merge**: rejected because it violates ADR-133 and turns
  governance into unsafe self-modification.
- **Do nothing beyond audits**: rejected because the system would remain
  self-observing rather than self-improving.

## Acceptance Criteria

```bash
python3 -m pytest tests/unit/test_self_improvement_loop.py -q
python3 -m pytest tests/unit/test_self_improvement_discipline_gate.py -q
scripts/cos-self-improvement-loop --profile core --json
scripts/cos-self-improvement-discipline-gate --profile core --json
```

The output must show `mode: propose_only`, `human_approval_required: true`, and
`auto_merge: false`.

## Cross-references

- `.cognitive-os/plans/architecture/headless-self-improvement-proposer-plan.md`
- `docs/architecture/headless-self-improvement-proposer.md`
- `lib/self_improvement_loop.py`
- `scripts/cos_self_improvement_loop.py`
- `scripts/cos-self-improvement-loop`

## Status

Accepted — structural contract normalized on 2026-05-04.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

