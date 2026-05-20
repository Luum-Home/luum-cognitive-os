---
adr: 330
title: Typed capability-ceiling signals
status: accepted
implementation_status: partial
date: '2026-05-20'
supersedes: []
superseded_by: null
implementation_files:
  - lib/capability_ceiling.py
  - tests/unit/test_capability_ceiling.py
tier: maintainer
tags: [agent-escalation, capability-ceiling, handoff]
classification_basis: operator-prioritized scoped revival from ADR-326 archived Phases 1+2
---

# ADR-330 — Typed capability-ceiling signals

## Status
Accepted — first slice implemented as read-only detection.

<!-- SCOPE: OS -->

**Date**: 2026-05-20
**Related**: ADR-326, ADR-228, ADR-251
**Work ID**: worker-g-p5-p6-20260520

## Context

ADR-326 tombstoned only Phase 3 of the older agent-escalation-capabilities plan.
Its key boundary is that retry budgets, retry-count tracking, budget gates, and
escalation cost reporting are already owned by ADR-228 and must not be revived
through this path. ADR-326 explicitly preserved the unique value of Phases 1+2:
typed capability-ceiling signals with structured context handoff.

Current escalation signals cover stuckness and failure symptoms such as repeated
errors, loops, and timeout risk. They do not distinguish a failure from a
capability ceiling: the agent may need deeper reasoning, a missing tool, more
context, or domain expertise. That difference matters because the next action is
not a generic retry. It is a structured handoff for a future orchestrator policy.

## Decision

Define exactly four typed capability-ceiling signals:

| Signal | Capability ceiling | Default handoff action |
|---|---|---|
| `NEEDS_DEEPER_REASONING` | Current model tier cannot complete the reasoning chain. | `upgrade_model` |
| `NEEDS_TOOL_ACCESS` | Current agent lacks a required tool or connector. | `grant_tool_or_human_review` |
| `NEEDS_MORE_CONTEXT` | Current context window or provided context is insufficient. | `expand_context` |
| `NEEDS_DOMAIN_EXPERT` | Task requires a specialist domain route. | `route_domain_expert` |

The first implementation slice is read-only. It may parse agent output and
return a structured handoff containing the signal, capability, recommended
action, attempted work, context summary, partial result, source agent, and
original task. It must set `auto_redispatch_allowed=false` and must not launch a
new agent.

## Boundaries

In scope:

- The four signal strings above.
- Read-only detection and classification.
- Structured handoff data for a future orchestrator.
- Tests proving no automatic re-dispatch is implied by the detector output.

Out of scope:

- Retry budgets.
- Escalation cost reporting.
- Generic failure retry taxonomy.
- Automatic model upgrades or agent re-launch.
- Governance readiness or maintainer telemetry changes.

## ADR-228 boundary

ADR-228 remains authoritative for failure classification, retry policies,
session budgets, graduated cost backpressure, circuit breakers, and idempotency.
Capability-ceiling signals do not create a new retry policy and do not alter
ADR-228's FailureClass taxonomy. If future work turns a handoff into an actual
re-dispatch, that work must call through the existing dispatch gate rather than
creating a parallel budget or retry path.

## ADR-326 boundary

ADR-326 remains the tombstone for Phase 3 budget/retry/cost scope. This ADR is a
scoped revival of the archived Phases 1+2 signal protocol only. It intentionally
stops before the historical plan's progressive escalation chain.

## Alternatives rejected

- Revive the full historical agent-escalation plan — rejected because ADR-326
  tombstoned the budget/retry/cost portions and ADR-228 owns that territory.
- Immediately auto re-dispatch on signal detection — rejected for this slice
  because operators need observable handoff objects before automation.
- Fold capability ceilings into ADR-228 FailureClass values — rejected because
  these signals describe capability boundaries, not provider or validation
  failures with retry policies.

## Consequences

- Agents and parsers get a stable vocabulary for capability ceilings.
- Operators can inspect handoff objects before any re-dispatch automation exists.
- Future automatic re-dispatch requires a separate ADR or amendment with dispatch
  gate integration, safety policy, and tests.
- The scope split prevents budget/retry duplication with ADR-228.

## Verification

```bash
python3 -m pytest tests/unit/test_capability_ceiling.py -q
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
