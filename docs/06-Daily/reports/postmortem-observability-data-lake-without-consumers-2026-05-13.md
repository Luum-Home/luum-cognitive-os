---
title: Post-Mortem — Observability Data Lake Without Consumers
date: 2026-05-13
status: draft
scope: maintainer
severity: HIGH
tags: [postmortem, observability, telemetry, slo, control-plane, structural-debt]
incident_window: 'Latent ~2026-04 onward — surfaced 2026-05-13 ~21:00 UTC-3 during ADR-302/303 session by operator question'
author: orchestrator-LLM (Claude) under operator review
related_adrs: [ADR-028, ADR-031, ADR-247, ADR-275, ADR-296, ADR-297, ADR-298, ADR-299, ADR-300, ADR-301, ADR-303]
---

# Post-Mortem — Observability Data Lake Without Consumers

## Severity classification

**HIGH.** Latent structural defect. No data loss, no user-facing outage. But the
project collects telemetry on every hook, every dispatch, every routing decision,
and every closure — and **acts on essentially none of it**. The orchestrator
makes decisions blind while the disk fills with metrics. A real 91-second
sub-agent spawn cold-start occurred today and would have continued occurring
indefinitely without an operator noticing if the operator had not asked
"probaste el rendimiento?".

This is the most expensive architectural anti-pattern in the codebase at the
time of this writing, larger in impact than any single ADR shipped today.

## Incident summary

During the 2026-05-13 ADR-303 work (sub-agent spawn benchmark), the operator
asked whether performance had been measured. The orchestrator extracted
**existing telemetry** from `.cognitive-os/metrics/hook-timing.jsonl` and found:

- 38 samples of `subagent-context-injector` hook duration (37 from today)
- p50 = 2.06 s
- p95 = **55.6 s**
- p99 = **90.9 s**
- max = **90.9 s** (one spawn this session took ~91 s before doing useful work)

This data had been continuously written by `scripts/hook-timing-wrapper.sh`
for at least 24 hours. **Nothing was reading it.** The orchestrator was making
delegation decisions without knowing that some spawns cost 90 s.

The operator observed that telemetry existed but was not being used to drive measurements or decisions.

That is the incident.

## Timeline

| When | Event |
|---|---|
| ~2026-04 | `hook-timing-wrapper.sh` began emitting durations per hook into `hook-timing.jsonl`. |
| 2026-04–05 | Multiple feature ADRs added their own `.jsonl` streams (ADR-049, ADR-273, ADR-275, ADR-296→ADR-303). Each appends; none reads cross-feature. |
| 2026-05-12 22:45 | 1 baseline sample for `subagent-context-injector` recorded. |
| 2026-05-13 (all day) | 37 more samples recorded, including 3 spawns > 30 s and 1 spawn at 90.9 s. |
| 2026-05-13 ~21:00 | Operator asks: "probaste el rendimiento?". Orchestrator runs `scripts/startup-benchmark.sh` (first time the file is non-empty since 2026-05-05) and discovers SessionStart at 9.7 s vs declared SLO of 2 s. |
| 2026-05-13 ~21:30 | Operator asks: "Sub-agent spawn cold-start?". Orchestrator extracts the n=38 sample window manually and surfaces p95 = 55.6 s, p99 = 90.9 s. |
| 2026-05-13 ~22:00 | Operator names the anti-pattern: *"no estamos haciendo nada con esta info."* |

## What we have (data collection)

| Stream | Volume | Continuously written by |
|---|---:|---|
| `.cognitive-os/metrics/hook-timing.jsonl` | **~38,000 records** | `scripts/hook-timing-wrapper.sh` (every hook call) |
| `.cognitive-os/metrics/llm-routing.jsonl` | growing | `lib/llm_routing_fallback.py` (ADR-297) |
| `.cognitive-os/metrics/skill-enrichment.jsonl` | tool-driven | `lib/skill_description_enricher.py` (ADR-299) |
| `.cognitive-os/metrics/llm-dispatch.jsonl` | per dispatch | `lib/dispatch.py` (ADR-049) |
| `.cognitive-os/metrics/skill-routing.jsonl` | per route | `hooks/skill-router-*.sh` |
| `.cognitive-os/metrics/startup-benchmark.jsonl` | on demand | `scripts/startup-benchmark.sh` (1 record total before today) |
| `.cognitive-os/audit/closure-trail.jsonl` | per close | `hooks/session-end-*.sh` (ADR-275) |

## What we don't have (consumers)

- **No aggregator** that reads any of these streams periodically.
- **No SLO comparator**: `manifests/cos-observability-slo.yaml` and similar declare targets but no job evaluates measurements against them outside `tests/unit/test_startup_budget.py` (which only runs when an operator manually invokes pytest).
- **No automated finding emission**: when a hook p95 exceeds budget for K consecutive windows, nothing pushes a finding to `.cognitive-os/tasks/control-plane-remediation.jsonl`.
- **No SessionStart banner extension**: the operator banner today shows skill-router suggestions but no "your last session had hook X at p95 = 55 s" line.
- **No Agent()-spawn warning**: the orchestrator does not consult recent SubagentStart p95 before delegating; it cannot say "expect a slow spawn".
- **No dashboard**: no `cos-observability-status` skill or `cos-metrics-snapshot` script that prints an aggregated view an operator can scan.

## Root cause

**Diffuse ownership of cross-cutting concern.** Each feature ADR (296→303 in
this single session, ADR-049 / ADR-275 / etc. previously) added a JSONL emitter
but treated reading as out-of-scope. The metrics architecture grew bottom-up
from individual emitters; no top-down ADR declared a consumer contract.

A secondary cause: COS already has a control-plane audit pattern (ADR-247,
`scripts/cos-control-plane-audit`, hourly / pre-public lanes) that emits
findings to `control-plane-remediation.jsonl`. That pattern is the right shape
for the consumer side — but no audit subscribes to the hook-timing /
dispatch / routing streams. The remediation queue is fed by static-analysis
audits today, not telemetry-driven ones.

## Detection

The defect surfaced because of an operator question, not a system signal.
Mean time to detect = unbounded; depended entirely on a human asking the
right question. This is the canonical "log everything, look at nothing" or
"data lake without consumers" anti-pattern in observability literature.

The 91-second spawn happened. It was recorded. Nothing alerted. The next
spawn would have produced the same result with the same silence.

## Impact

- **Performance debt invisible.** Today's discovery: SessionStart SLO breach
  (9.7 s vs 2 s budget, 4.8× over) and sub-agent spawn p95 = 55.6 s.
  Both went unflagged for ≥ 24 h.
- **Decisions made blind.** The orchestrator dispatched 4–5 parallel
  sub-agents during this session without knowing any individual spawn
  might cost 90 s.
- **Trust loss with operator.** When the operator asks "probaste el
  rendimiento?" and the honest answer is "the data exists but nobody
  reads it", that erodes the contract that COS reports its own state
  faithfully.
- **ADR drift.** Six new ADRs shipped today (ADR-296→ADR-301, ADR-303)
  each added emitters but none addressed consumers. The pattern is
  self-reinforcing.

## Recovery / mitigation taken in-session

1. **`startup-benchmark.jsonl` re-populated** (was empty since 2026-05-05).
2. **`test_startup_budget.py` budget tightened 10 s → 2 s** (commit `fb1b0500`)
   so the SessionStart breach now surfaces as a CI signal instead of hiding
   under a generous budget.
3. **`lib/agent_spawn_benchmark.py` shipped (ADR-303, commit `<later>`)** as
   a synthetic baseline harness. **Acknowledged inadequate** — the
   measurement is sub-second synthetic vs 55 s real telemetry, a 150× gap
   the agent itself flagged. A Phase 2 refactor to consume `hook-timing.jsonl`
   directly is documented as the next step.
4. **This post-mortem.**

## What went well

- **Telemetry collection is correct.** The data was there, accurate, and
  recoverable in one grep. The infrastructure to know is in place.
- **`hook-timing-wrapper.sh` provides clean per-hook duration data with
  timestamps.** No reconstruction needed.
- **The operator caught it.** A skilled operator asking the right question
  reaches the conclusion in two queries.

## What went wrong

- **No subscriber pattern.** Each emitter assumed someone would read its
  output; nobody did.
- **No SLO enforcement loop.** Budgets are declared (`cos-observability-slo.yaml`,
  `test_startup_budget.py`) but only checked when manually invoked.
- **No remediation feedback.** Even when audits do produce findings
  (`control-plane-remediation.jsonl` has 100+ blocking entries), there is no
  triage loop. They accumulate.
- **No banner integration.** The SessionStart banner that the operator sees
  on every interaction does not include a "your system has 3 unresolved
  performance findings" line.
- **Test infra blind to runtime.** Tests can pass on the wrong Python
  version without alerting. Same anti-pattern (signal without consumer)
  applied to test infrastructure itself.

## Action items

| # | Action | Type | ADR | Owner |
|---|---|---|---|---|
| 1 | Telemetry Aggregator: hourly job reads JSONL streams, computes p50/p95/p99/max per (hook, event), compares against SLO manifest, pushes findings to `control-plane-remediation.jsonl`. | feature | **ADR-304** | next session |
| 2 | SessionStart banner extension: at session boot, read top 3 unresolved remediations from the queue and inject into operator banner. | feature | ADR-304 | next session |
| 3 | Agent()-spawn warning: before dispatching a sub-agent, check recent SubagentStart p95; if > 1.5 × budget, log warning "delegation cost is elevated". | feature | ADR-304 | next session |
| 4 | Auto-tune proposer: if hook X p95 > budget for K consecutive windows AND hook X has no stdout emission, propose async promotion (the manual move done in commit `c37a8e73` today). | feature | ADR-304 | next session |
| 5 | Test runtime invariants: `tests/conftest.py` asserts Python ≥ 3.11 AND `sys.executable` is under `.venv/`. Operator catch on bus benchmark Python 3.9 vs 3.14 mismatch is the trigger. | hygiene | **ADR-305** | next session |
| 6 | ADR-303 refactor: pivot `lib/agent_spawn_benchmark.py` from synthetic measurement to aggregator over `hook-timing.jsonl`. The synthetic harness reported 386 ms; real telemetry reports p95 = 55 s — a 150× honesty gap. | refactor | ADR-303 §Phase 2 | next session |
| 7 | Per-stream consumer audit: for every existing `.jsonl` under `.cognitive-os/metrics/`, document its consumer (or "none — feed to ADR-304 aggregator"). | docs | ADR-304 follow-up | next session |
| 8 | Pre-existing `control-plane-remediation.jsonl` triage: 100+ blocking findings have accumulated since 2026-05-11. Either resolve, downgrade to warn, or batch-close. | hygiene | ADR-304 prerequisite | next session |
| 9 | Operator-facing observability status command: `cos status --observability` prints aggregated metrics view (top 5 hook offenders, recent dispatch failures, current remediation queue size). | UX | ADR-304 | next session |
| 10 | The SLO catalogue (ADR-028) should explicitly enumerate which audits enforce which SLOs, and which SLOs have no enforcement today. The gap is itself a finding. | docs | ADR-028 update | next session |

## Lessons (blameless)

1. **Adding an emitter is not the same as adding observability.** Future
   feature ADRs should EITHER hook into an existing aggregator OR carry
   an explicit consumer slice.
2. **Generous budgets hide regressions.** The 10 s budget on
   `test_startup_budget.py` was set to "not break CI on the current
   baseline" — exactly the behavior that prevents the test from doing its
   job. Tightening to the declared SLO (2 s) is uncomfortable today but
   correct.
3. **Operator questions are not a substitute for automated alerting.** The
   project is on track to ship more emitters every sprint; without a
   consumer mandate, each one increases the disk usage and the false
   sense of observability without improving signal.
4. **The fix has high ROI.** ADR-304 is the highest-leverage single piece
   of work the project could ship next. It does not require new models,
   new licenses, or new tooling — just a Python script that reads files
   COS already writes and emits findings into a queue COS already has.

## Related

- ADR-028 — SLO catalogue + error budget cadence (declares; does not enforce continuously)
- ADR-031 — Continuous Aspirational/Dormant/Real audit (the *audit-side* equivalent of what telemetry needs)
- ADR-247 — Postmortem regression audit (this post-mortem will eventually feed that)
- ADR-275 — Closure & projection primitives (the one consumer that exists today)
- ADR-296 → ADR-303 — all emitters added in 2026-05-12/13; none with a consumer slice
- `docs/06-Daily/session-2026-05-13-skill-router-overhaul.md` — narrative of the session that surfaced this
- `docs/06-Daily/reports/postmortem-cross-session-collision-2026-05-05.md` — prior post-mortem in the same series

---

_Drafted by orchestrator-LLM (Claude) at operator request after the operator
named the anti-pattern: "no estamos haciendo nada con esta info." Operator
review pending._
