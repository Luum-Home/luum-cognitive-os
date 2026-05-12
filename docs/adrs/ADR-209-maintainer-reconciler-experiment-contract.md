---
adr: 209
title: Maintainer Reconciler Experiment Contract
status: accepted
implementation_status: partial
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: Some proposals remain unexecutable until metrics exist.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-209 — Maintainer Reconciler Experiment Contract

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted — experiment schema slice active  
**Date**: 2026-05-06  
**Related**: ADR-201, ADR-204, ADR-205, ADR-207  
**Source**: `.cognitive-os/strategy/research/06-external-patterns-benchmark.md`, `.cognitive-os/strategy/research/08-self-improvement-roadmap.md`

---

## Context

External closed-loop systems converge on a pattern: deterministic controllers,
declarative desired state, predeclared experiment metrics, canary scopes,
rollback thresholds, and human-owned promotion. None safely rewrites its own
rules without boundaries.

ADR-201 defines proposals. This ADR defines how a maintainer change becomes an
experiment.

## Decision

Model Maintainer v1 as a reconciler over typed COS resources, not as a freeform
agent loop.

Every executable maintainer change must create an **Experiment Contract** before
application:

- target surface;
- desired state;
- canary scope;
- success metrics;
- guardrail metrics;
- rollback threshold;
- measurement window;
- human approval;
- owner;
- cooldown;
- outcome action.

LLMs may draft proposals, but deterministic code evaluates whether an experiment
passes, fails, or is inconclusive.

## Hard rules

- Maintainer fails open; it must not block critical launch paths.
- No two maintainer loops may act on the same surface without an arbiter.
- Optimizing one metric requires at least one guardrail co-metric.
- PR acceptance is not correctness.
- Auto-execute requires a named reviewed playbook, not an ad-hoc proposal.

## Consequences

### Positive

- Maintainer behavior mirrors mature controller/rollout systems.
- Experiments become reviewable and replayable.
- Outcome failure is measurable.

### Negative / trade-offs

- More schema before action.
- Some proposals remain unexecutable until metrics exist.

## Implementation slices

1. [x] Add `manifests/maintainer-experiment-schema.yaml`.
2. [x] Add `lib/maintainer_experiment.py`.
3. [ ] Require experiment design for ADR-201 proposals that mutate behavior.
4. [ ] Add canary fixture for router-confidence change.
5. [x] Add outcome evaluator with pass/fail/inconclusive statuses.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_maintainer_experiment_contract.py -q
python3 -m pytest tests/behavior/test_maintainer_canary_flow.py -q
```

The behavior test must prove a router-confidence experiment with a failing
guardrail is marked failed and does not promote.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
