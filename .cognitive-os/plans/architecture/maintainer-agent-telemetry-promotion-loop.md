---
related-adr: ADR-201
---

# Maintainer Agent and Telemetry Promotion Loop Plan

## Goal

Close the self-improvement ownership gap by adding a scheduled, bounded
maintainer agent that converts Cognitive OS telemetry into human-reviewed
improvement proposals with measurable impact.

## Phase 0 — Bound the claim

- [x] Document the gap in `docs/reports/self-improvement-maintainer-agent-gap-2026-05-06.md`.
- [x] Propose ADR-201 for the maintainer agent and telemetry promotion loop.
- [ ] Update product messaging to avoid claiming continuous self-improvement
      until the maintainer loop is implemented and smoke-tested.

## Phase 1 — Canonical performance ledger — BLOCKER

No later ADR-201 slice should be treated as production-ready until this phase
compiles a validated ledger from fixture and live telemetry.

- [x] Add `lib/performance_ledger.py`.
- [x] Add `scripts/cos-performance-ledger`.
- [x] Add signal-quality validation before rollups: valid/suspect/corrupt rows,
      malformed JSON, unsourced trust-score defaults, impossible values, and
      identity corruption such as `skill: matias`.
- [ ] Roll up skill metrics: invocations, success/failure, override rate,
      trust-report pass rate, verification pass rate, time-to-complete.
- [ ] Roll up provider/router metrics: chosen provider, fallback rate, error
      class, latency, cost, retry count.
- [ ] Roll up primitive metrics for selected high-value primitives first:
      dispatch, skill routing, state retention, repair, validation.
- [ ] Preserve source metric references for auditability.
- [ ] Emit harness metadata while keeping output rows/proposals harness-agnostic.
- [x] Store primary ledger in `.cognitive-os/ledgers/performance-ledger.sqlite`,
      export audit rows to `.cognitive-os/metrics/performance-ledger.jsonl`, and
      generate `.cognitive-os/reports/performance-ledger-latest.json`.
- [x] Add deterministic proposal ids for deduplication: hash(surface +
      degradation pattern + day window).
- [x] Add retention policy for generated ledger artifacts.

## Phase 2 — PromoteFromTelemetry primitive

- [x] Add `lib/promote_from_telemetry.py`.
- [x] Add `scripts/cos-promote-from-telemetry`.
- [ ] Detect repeated skill override/degradation patterns.
- [ ] Detect provider fallback or compatibility drift.
- [ ] Detect dormant/aspirational primitives with no recent evidence.
- [x] Emit proposal JSON with source evidence, candidate action, severity, self-confidence, allowed write
      paths, required tests, rollback, experiment design, cooldown, and human approval requirement.
- [x] Suppress duplicate proposals through stable finding ids based on surface + degradation pattern + day window; proposal cooldown is part of the schema.

## Phase 3 — Maintainer agent runner

- [x] Add `scripts/cos-maintainer-agent --once --dry-run --json`.
- [x] Call the performance ledger and `PromoteFromTelemetry` primitive.
- [x] Write proposals under `.cognitive-os/improvements/proposals/` only when
      explicitly requested with `--write-proposals` and not `--dry-run`.
- [x] Add a single-run lock; cooldown/budget remain schema/model-policy controls until scheduled service mode lands.
- [x] Declare ADR-164 Host CLI Bridge Security Boundary in runner output and keep this slice propose-only; executable mutations remain blocked.
- [x] Use sonnet-class models by default for scheduled proposal drafting and reserve opus-class models for P0/P1 ambiguity, architecture decisions, or final adversarial review.
- [x] Support local/headless dry-run invocation without dashboard dependency; future cloud scheduling remains a later service-mode slice.
- [x] Keep merge and promotion human-approved.

## Phase 4 — Validation and smoke tests

- [ ] Unit-test ledger normalization from fixture metrics.
- [ ] Unit-test signal-quality quarantine before rollups.
- [x] Unit-test proposal generation and duplicate suppression.
- [x] Behavior-test full loop: fixture telemetry -> maintainer agent -> one
      bounded, human-approved proposal.
- [x] Failure-test no-self-bite behavior: dirty telemetry blocks only maintainer promotion, not normal agent work.
- [ ] Add a headless smoke path that runs the maintainer agent in dry-run mode
      inside the service/container drill.

## Phase 5 — Impact measurement

- [ ] Add post-change impact records after accepted proposals land.
- [ ] Implement outcome-failure protocol: mark regressed/inconclusive, quarantine pattern, open manual investigation, require approval for rollback, and penalize maintainer confidence for similar future patterns.
- [ ] Compare baseline and candidate metrics over a declared window.
- [ ] Mark proposals as improved, neutral, regressed, or inconclusive.
- [ ] Feed regressions back into `PromoteFromTelemetry` as first-class signals.

## Non-goals

- No auto-merge.
- No direct mutation of live runtime surfaces.
- No dashboard-first implementation.
- No external adoption claims from maintainer-owned evidence.
- No skill/provider demotion without reversible archive/tombstone path.

## Validation commands

```bash
python3 -m pytest tests/unit/test_performance_ledger.py -q
python3 -m pytest tests/unit/test_performance_ledger_signal_quality.py -q
python3 -m pytest tests/unit/test_promote_from_telemetry.py -q
python3 -m pytest tests/unit/test_maintainer_proposals.py -q
python3 -m pytest tests/behavior/test_maintainer_agent_loop.py -q
scripts/cos-performance-ledger --json
scripts/cos-promote-from-telemetry --dry-run --json
scripts/cos-maintainer-agent --once --dry-run --json
```
