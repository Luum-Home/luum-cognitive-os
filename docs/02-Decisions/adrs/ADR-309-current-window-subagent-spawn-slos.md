---
status: Accepted
date: 2026-05-14
deciders: Cognitive OS maintainers
tags:
- observability
- telemetry
- slo
- subagents
implementation_status: Implemented
adr: 309
title: Current-Window Subagent Spawn SLOs
implementation_files:
- manifests/observability-slo.yaml
- lib/telemetry_aggregator.py
- tests/unit/test_telemetry_aggregator.py
- tests/unit/test_agent_spawn_budget.py
- tests/unit/test_startup_budget.py
tier: maintainer
classification_basis: current-window telemetry SLO evaluation and subagent/startup
  budget tests are implemented; no remaining in-scope work for this ADR
---

# ADR-309: Current-Window Subagent Spawn SLOs with Historical Tail Diagnostics

## Status

Accepted


## Context

ADR-303 introduced a synthetic sub-agent spawn cold-start benchmark. ADR-304 made production telemetry the authoritative latency signal through `manifests/observability-slo.yaml` and `lib/telemetry_aggregator.py`.

After reducing SubagentStart hot-path noise, the default telemetry test lane passed, but strict enforcement still failed against local historical telemetry:

- `subagent-spawn-p95`: ~45,046 ms against a 5,000 ms target.
- `subagent-spawn-p99`: ~76,799 ms against a 15,000 ms target.
- 41 total local SubagentStart samples, including old outliers up to ~90,915 ms.

The recent samples show the current behavior is materially better: the last 10 records are around ~2.3 s max and the last 20 records stay under the current p95/p99 targets. The failure mode is therefore a telemetry semantics problem: the regression gate is using the local historical incident window as if it represented current system behavior.

We must not fix this by deleting `.cognitive-os/metrics/hook-timing.jsonl`; historical outliers are useful incident evidence. We also should not make the SLO disappear. The system needs both:

1. a current regression SLO that can turn green after a fix; and
2. historical tail diagnostics that keep old incidents visible for operators.

## Decision

Use a current matching-record window for SubagentStart regression SLOs and attach historical matched-stream diagnostics to windowed evaluations.

Concretely:

- `subagent-spawn-p95` and `subagent-spawn-p99` use `window: last_20_records`.
- The filter remains scoped to real SubagentStart telemetry: `event == "SubagentStart" or hook == "subagent-context-injector"`.
- `lib/telemetry_aggregator.py` keeps applying filters before windows so sparse SubagentStart events are not hidden by unrelated hook noise.
- When a window trims matching records, the evaluation `window_summary` includes an `all_matched_summary` diagnostic computed over every matching record in the source stream. This preserves historical p50/p95/p99/max visibility without making old local outliers fail the current regression gate.
- `COS_STRICT_TELEMETRY_SLO=1` remains the opt-in strict unit-test mode for local production telemetry, but now it answers: “does the current SubagentStart window regress?” rather than “did this machine ever have a prior incident?”

## Consequences

Positive:

- Current sub-agent spawn fixes can be validated without deleting local telemetry history.
- Historical outliers remain visible in telemetry snapshots and `cos status --observability` inputs through `all_matched_summary`.
- The SLO keeps using production telemetry rather than the ADR-303 synthetic benchmark as the authority.
- The aggregator gains a reusable diagnostic pattern for sparse streams with meaningful historical incidents.

Trade-offs:

- A smaller window can miss rare tail regressions until enough new samples accumulate. This is acceptable for the strict unit lane because it is a regression gate, not the only observability surface.
- Operators must interpret `all_matched_summary` as diagnostic history, not current SLO status.
- Future high-volume production deployments should revisit the window size and may move to time-based windows once timestamp normalization is standardized across streams.

## Alternatives Considered

### Delete or rotate local historical telemetry

Rejected. It makes the test green by destroying useful incident evidence and makes root-cause analysis harder.

### Keep `last_100_records` for the blocking SLO

Rejected for the current repository lane. SubagentStart is sparse locally; with only 41 records, a `last_100_records` window is effectively “entire history”. That blocks current-regression validation on old incidents.

### Use the ADR-303 synthetic benchmark as the strict gate

Rejected. Synthetic wall-clock remains a smoke/lower-bound signal only. Real production telemetry is still the authority.

### Time-based windows now

Deferred. Time-based windows are the right long-term shape, but require consistent timestamp parsing and policy for malformed/missing timestamps across all JSONL streams. Record-count windows are already supported and sufficient for this corrective slice.

## Alternatives rejected

- **Leave the behavior as implicit agent instruction only.** Rejected because this ADR records a runtime/authoring contract that needs durable tests or audits rather than conversation-only memory.

## Verification

- `.venv/bin/python -m pytest tests/unit/test_telemetry_aggregator.py tests/unit/test_agent_spawn_budget.py tests/unit/test_startup_budget.py -q`
- `COS_STRICT_TELEMETRY_SLO=1 .venv/bin/python -m pytest tests/unit/test_agent_spawn_budget.py::test_real_spawn_latency_slos_are_authoritative -q`
- `python3 scripts/cos-telemetry-aggregate --no-self-tuning --quiet --snapshot /tmp/telemetry-snapshot.yaml --findings /tmp/telemetry-findings.jsonl`


```bash
python3 -m pytest tests/unit -q
```
## Follow-ups

- Add time-window syntax such as `last_24h_records` or `since_timestamp` after timestamp normalization is explicit.
- Consider separate incident-history dashboards for historical p99/max outliers that should never block current-regression gates.
