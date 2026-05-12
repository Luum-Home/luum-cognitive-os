---

adr: 180
title: Lifecycle Promotion Activation — Concrete Proposers and Hook Wiring
status: accepted
implementation_status: implemented
date: 2026-05-05
supersedes: []
superseded_by: null
extends: ADR-177
implementation_files:
  - scripts/cos-promotion-proposer
  - scripts/cos_promotion_proposer.py
  - scripts/cos-demotion-proposer
  - scripts/cos_demotion_proposer.py
  - scripts/cos_doctrine_proposer.py
  - hooks/promotion-proposer-weekly.sh
  - tests/unit/test_promotion_proposer.py
  - tests/unit/test_demotion_proposer.py
  - tests/integration/test_doctrine_proposer_metrics.py
  - tests/contracts/test_promotion_propose_only.py
tier: maintainer
tags: [skills, lifecycle, promotion, demotion, doctrine, dogfood, propose-only]
---
# ADR-180: Lifecycle Promotion Activation — Concrete Proposers and Hook Wiring

## Status

Accepted.

## Context

ADR-177 ("Activate Skill Lifecycle Promotion Ladder") records the doctrinal
decision to wake the dormant promotion ladder. The `lib/skill_lifecycle_promoter.py`
module landed there as the first cut, embedded inside the doctrine-proposer.

The gap analysis in `docs/reports/lifecycle-promotion-gap-2026-05-05.md`
documents two operational symptoms that ADR-177 alone does not resolve:

1. Sandbox skills (18 on disk) never promote because no scheduled job evaluates
   them against SkillStore evidence.
2. Advisory and blocking skills with zero recent invocations never demote
   because no scheduled job inspects them.
3. The doctrine-proposer itself does not write to
   `.cognitive-os/metrics/doctrine-proposals.jsonl`, so there is no evidence
   trail of when proposals were generated, with what input signals.

ADR-176 (SkillStore SQLite schema) made the data substrate available. ADR-177
made the conceptual decision. ADR-180 is the operational activation layer:
two concrete propose-only scripts, a weekly hook, propose-only contract tests,
and a metrics emission upgrade for the doctrine-proposer.

This ADR is intentionally narrow: it does not change ladder thresholds,
governance class meanings, or the meaning of `lifecycle_state` in
`manifests/primitive-lifecycle.yaml`. It only adds a propose-only mechanism
that operators can run, audit, and approve.

## Decision

Activate the lifecycle promotion ladder operationally with these artifacts:

### 1. `scripts/cos-promotion-proposer`

Reads `lib.skill_store.SkillStore` and `manifests/primitive-lifecycle.yaml`.
For each primitive at `lifecycle_state: sandbox`, query SkillStore for
`record_count`, `success_rate`, and `judge_avg_score`. If thresholds are met:

- `record_count >= 50`
- `success_rate >= 0.85`
- `judge_avg >= 0.8`

emit a propose-only artifact at
`docs/reports/promotion-proposals/<YYYY-MM-DD>/<skill-name>.md`. The script
**never** modifies `manifests/primitive-lifecycle.yaml` or the registry lock.
All activity is logged to `.cognitive-os/metrics/promotion-proposals.jsonl`.

CLI flags:

- `--dry-run` (default): print what would be proposed, write nothing.
- `--apply`: write proposal artifacts (still does not modify any manifest).
- `--skill <name>`: limit evaluation to one primitive.
- `--threshold-records N` / `--threshold-success P` / `--threshold-judge P`: override defaults.

Killswitch: `DISABLE_PROMOTION_PROPOSER=1` in environment short-circuits.

### 2. `scripts/cos-demotion-proposer`

For each primitive at `advisory` or `blocking` with zero records in
`record_count` over the demotion window (default 90 days), emit a demotion
proposal at `docs/reports/demotion-proposals/<YYYY-MM-DD>/<skill-name>.md`.
Same propose-only contract; logs to
`.cognitive-os/metrics/demotion-proposals.jsonl`.

### 3. Doctrine-proposer metrics upgrade

`scripts/cos_doctrine_proposer.py` now emits one event per run to
`.cognitive-os/metrics/doctrine-proposals.jsonl` with `input_signals`:

- `skillstore`: hash of latest SkillStore snapshot (or null when absent)
- `dogfood`: dogfood-score latest score (or null)
- `drift`: recent drift detector status (or null)
- `aspirational`: aspirational-audit summary (or null)

Emission happens unconditionally (even on `--dry-run`-like paths) so the
metrics file becomes a heartbeat for the doctrine-proposer.

### 4. Weekly hook

`hooks/promotion-proposer-weekly.sh` registered in `SessionStart`. Throttled
to at most one run per 7 days via a marker file
(`.cognitive-os/metrics/.last-promotion-proposer`). Always async,
non-blocking, fail-open.

### 5. Propose-only invariant test

`tests/contracts/test_promotion_propose_only.py` records SHA-256 of
`manifests/primitive-lifecycle.yaml` and `manifests/agentic-primitive-registry.lock.yaml`
before and after running the promoter and the demoter against a synthetic
SkillStore. Both files MUST be byte-identical after both runs. Failure of
this test is a CRITICAL blocker.

## Consequences

### Positive

- Operators have a dated, reviewable evidence trail of every promotion or
  demotion proposal.
- Metrics emission enables future SLO tracking (e.g., proposal-to-decision
  latency, proposal acceptance rate).
- The propose-only invariant test makes auto-apply regression unambiguous.
- The weekly hook makes the ladder truly active (not aspirational) without
  blocking sessions.

### Negative / Trade-offs

- Threshold values (50 records, 0.85 success, 0.8 judge avg) are conventional;
  not yet validated against COS-specific historical data. First 90 days of
  operation will calibrate them.
- Demotion threshold (90 days no-records) is arbitrary. It may over-demote
  rare-but-important skills (e.g., release-os, audit-integrity). Operators
  can override per-skill via `--skill` for now; a per-skill grace allow-list
  is left as a follow-up if the false-positive rate is high.
- The metrics file grows monotonically; rotation is a follow-up.

## Falsifiable Claim

90 days after activation:

1. At least 5 sandbox skills should promote based on real evidence. If 0
   promote despite 18+ sandbox skills accumulating evidence, the mechanism
   is broken (thresholds wrong, query wrong, or evidence pipeline broken).
2. `dogfood_score.skill_coverage` should rise from 24.07 toward 60 within
   6 months.

If neither claim holds at 90 days, this ADR is open to revision.

## Acceptance Criteria

```bash
python3 -m pytest tests/unit/test_promotion_proposer.py -q
python3 -m pytest tests/unit/test_demotion_proposer.py -q
python3 -m pytest tests/integration/test_doctrine_proposer_metrics.py -q
python3 -m pytest tests/contracts/test_promotion_propose_only.py -q
DISABLE_PROMOTION_PROPOSER=1 bash hooks/promotion-proposer-weekly.sh   # exits 0
bash scripts/cos-promotion-proposer --dry-run                          # exits 0
```

## Cross-references

- ADR-138 — flow contract schema; lifecycle ladder formal definition.
- ADR-133 — auto-skill-generation governance (sandbox-only auto-apply).
- ADR-134 — closed-loop self-improvement (propose-only at promotion).
- ADR-135 — self-evolving doctrine proposer (propose-only).
- ADR-176 — SkillStore SQLite schema (data substrate for this ADR).
- ADR-177 — Activate Skill Lifecycle Promotion Ladder (doctrinal precondition).
- `docs/reports/lifecycle-promotion-gap-2026-05-05.md` — gap analysis that
  motivated this ADR.

## Verification

Implemented and tested on 2026-05-05 with unit, integration, and contract
test lanes plus a propose-only SHA invariant guard.

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

## Operational Guide

### What changes for the operator

Before this ADR, the skill lifecycle promotion ladder (declared in ADR-177) was doctrinal but not operational: sandbox skills never promoted because no scheduled job evaluated them, and skills with zero invocations never demoted. The doctrine-proposer had no metrics trail.

After this ADR:

| Surface | Before | After |
|---|---|---|
| Sandbox skill promotion | Never happened automatically | `scripts/cos-promotion-proposer` evaluates against SkillStore thresholds and writes dated proposals |
| Skill demotion | Never happened automatically | `scripts/cos-demotion-proposer` evaluates zero-invocation skills against 90-day window and writes dated proposals |
| Doctrine-proposer trail | No evidence log | Emits to `.cognitive-os/metrics/doctrine-proposals.jsonl` on every run |
| Weekly activation | None | `hooks/promotion-proposer-weekly.sh` (SessionStart, throttled to once per 7 days) |
| Manifest safety | No invariant | `tests/contracts/test_promotion_propose_only.py` fails immediately if either proposer modifies `primitive-lifecycle.yaml` or `agentic-primitive-registry.lock.yaml` |

### What this answers (and what it doesn't)

**Answers:**
- "Should sandbox skill X be promoted?" — Run `scripts/cos-promotion-proposer --skill X --dry-run`; output shows whether thresholds are met (50 records, 0.85 success rate, 0.8 judge avg).
- "Which skills are candidates for demotion?" — Run `scripts/cos-demotion-proposer --dry-run`; output lists advisory/blocking skills with zero records in the last 90 days.
- "Did the promoter ever modify a live manifest?" — Check `tests/contracts/test_promotion_propose_only.py`; if it passes, the answer is no.

**Does not answer:**
- "Should I accept this proposal?" — Proposals in `docs/reports/promotion-proposals/` and `docs/reports/demotion-proposals/` require operator review and manual application.
- "Are the thresholds well-calibrated?" — The initial thresholds (50 records, 0.85 success, 0.8 judge avg, 90-day demotion window) are conventional; the first 90 days of operation will calibrate them via the metrics log.

### Daily operational pattern

1. **Automated**: the weekly hook fires automatically during SessionStart (at most once per 7 days). No operator action needed for normal operation.
2. **On-demand check**: `scripts/cos-promotion-proposer --dry-run` or `scripts/cos-demotion-proposer --dry-run` to see current candidate state.
3. **When a proposal appears** in `docs/reports/promotion-proposals/<date>/` or `docs/reports/demotion-proposals/<date>/`: review the evidence, then manually apply the promotion/demotion to `manifests/primitive-lifecycle.yaml` if appropriate.
4. **Disable**: set `DISABLE_PROMOTION_PROPOSER=1` to short-circuit the promoter.

### Reading guide for cold readers

1. ADR-177 is the doctrinal precondition — read it first for the lifecycle ladder definition and `lifecycle_state` meanings in `manifests/primitive-lifecycle.yaml`.
2. ADR-176 (SkillStore) is the data substrate — the proposers query `lib.skill_store.SkillStore` directly.
3. The propose-only invariant test at `tests/contracts/test_promotion_propose_only.py` is the safety guarantee: if it passes, no live manifest was modified.
4. The `docs/reports/lifecycle-promotion-gap-2026-05-05.md` gap analysis documents the three operational symptoms that motivated this ADR — useful context for understanding why the weekly hook and metrics trail were needed.

## Alternatives rejected

- **Leave the decision implicit** — rejected because ADR slots must remain self-describing and audit-safe after multi-agent collision recovery.

