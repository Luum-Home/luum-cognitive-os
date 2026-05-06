# Self-Improvement Maintainer Agent Gap — 2026-05-06

**Scope**: why Cognitive OS still depends too much on humans or ad-hoc agents to notice broken skills, routing drift, aspirational primitives, and provider degradation even though it already records many metrics.

## Short answer

Cognitive OS has many self-observation and propose-only primitives, but it does
not yet have a permanent maintainer agent with an ownership contract over the
SO's own telemetry. The current shape is closer to a registry plus audit tools
than to a closed-loop maintenance service.

The missing product capability is not another skill package format. Hermes-like
skill packaging solves distribution: package a capability so a host can consume
it. Cognitive OS also needs a consumer, producer, and evaluator that continuously
uses skills, measures outcomes, and proposes/refines new primitives from observed
performance.

Analogy:

| Shape | What it does | Why it is not enough |
|---|---|---|
| Skill provider / registry | Packages capabilities for hosts. | Does not own runtime outcomes. |
| Human-invoked agent session | Solves a user's current task. | Does not continuously improve COS itself. |
| Maintainer agent | Reads COS telemetry, detects drift, proposes changes, verifies impact, asks for approval. | This is the missing loop owner. |

## Friction stack

| Depth | Gap | Evidence / current reading | Consequence |
|---:|---|---|---|
| 1 | No permanent maintainer agent | Existing agents are mostly task/session scoped. ADR-134 defines a propose-only loop, but Phase 4 background runner is still open. | Nobody has a standing contract to read COS's own metrics and improve COS. |
| 2 | No `PromoteFromTelemetry` primitive | Metrics such as redirects, dispatch fallbacks, skill feedback, cost events, and action receipts exist, but the promotion path is not a first-class primitive. | Repeated evidence remains passive until a human notices it. |
| 3 | No canonical skill performance ledger | Existing skill metrics are distributed across feedback, invocations, archives, route/dispatch logs, and trust reports. | The router cannot reliably lower confidence or propose rewrites from a single fitness view. |
| 4 | Dispatcher loop is not closed | Dispatch metrics can record provider fallbacks, but there is no automatic model-compatibility proposal workflow. | Provider degradation becomes tribal knowledge instead of an ADR/update candidate. |
| 5 | Aspirational primitives do not auto-decommission | ADR-031 identifies aspirational/dormant/real status, but deletion/demotion still depends on manual follow-through. | Dormant surface accumulates and erodes trust in product claims. |
| 6 | Router false positives do not become learning signals | A strategy/risk conversation produced a `/auto-rollback` suggestion even though the user was critiquing the suggestion, not requesting rollback. | Dangerous/recovery skills can be suggested in meta-discussions unless negative evidence is captured and routed into improvement proposals. |

## Why previous attempts did not close the loop

The implicit formula was wrong:

```text
agentic primitives + written protocol = self-improvement
```

The operational formula needs an owner:

```text
agentic primitives + maintainer agent + scheduler + telemetry ledger + human-gated promotion = self-improvement
```

If no agent owns the behavior continuously, the behavior does not happen. A repo
with hundreds of ADRs, dozens of metric streams, and many skills can still fail
to improve itself if every loop waits for a human-initiated session.

## Current adjacent work

This gap does not invalidate existing self-improvement work. It clarifies the
missing layer above it:

- ADR-083 defines governed self-improvement boundaries.
- ADR-090 defines skill degradation and repair signaling.
- ADR-095 defines skill synthesis from successful repeated workflows.
- ADR-134 defines a headless propose-only self-improvement primitive.
- ADR-135 defines doctrine proposals without live runtime mutation.
- ADR-146/147 define primitive readiness and capability coverage surfaces.
- ADR-199/200 show the recent pattern for turning passive audit into bounded safe automation.

The maintainer-agent loop should consume these primitives instead of replacing
them.

## New dogfood evidence — router suggested `/auto-rollback` in a meta-discussion

During the same session, a user reported that an agent/router suggested
`/auto-rollback` while discussing architecture and private-content portability.
That was not an operator request to roll back a failed apply. It was a
meta-discussion about a bad suggestion.

This is exactly the kind of signal ADR-201 must consume:

```text
router suggestion -> user/agent rejects as irrelevant or scary -> telemetry row -> PromoteFromTelemetry proposal
```

The current rollback runtime remains approval-gated by ADR-107, so the immediate
risk is not silent destructive git. The product risk is that the router lacks a
negative-evidence loop for safety/recovery skills and will keep repeating scary
or irrelevant suggestions until a human notices.

## Required product claim correction

Unsafe claim:

> Cognitive OS continuously improves itself.

Accurate current claim:

> Cognitive OS is self-observing and can generate governed improvement proposals, but the permanent maintainer-agent loop is not complete yet.

Target claim after implementation:

> Cognitive OS runs a bounded maintainer agent that continuously converts telemetry into human-reviewed improvement proposals, validates candidate changes, and tracks post-change impact.

## Acceptance criteria for closing the gap

The gap is not closed until all are true:

1. A scheduled maintainer agent runs in local/headless mode without human prompt.
2. The agent reads a canonical skill/provider/primitive performance ledger.
3. Repeated telemetry deltas produce typed proposals, not just warnings.
4. Proposals declare source evidence, allowed write paths, expected tests, rollback, and approval gates.
5. Candidate changes are validated against baseline metrics before promotion.
6. A post-change impact ledger records whether the change improved or regressed performance.
7. The loop is safe by default: no auto-merge, no live runtime mutation, no core/team promotion without human approval.

## Non-goals

- No autonomous merge to main.
- No silent rewrite of live `hooks/`, `rules/`, or root `skills/`.
- No fabricated ROI or adoption evidence.
- No cloud dependency for the local maintainer loop.
- No dashboard-first implementation. The loop must work as CLI/service behavior first.

## Recommended next decision

Adopt ADR-201: **Maintainer Agent and Telemetry Promotion Loop**.

That ADR should define the permanent owner, the performance ledgers, the
`PromoteFromTelemetry` primitive, and the approval boundary. Implementation
should start narrow: skill/router/provider telemetry before broader doctrine or
architecture changes.
