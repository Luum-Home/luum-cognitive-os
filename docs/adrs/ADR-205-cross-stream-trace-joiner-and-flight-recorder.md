# ADR-205 — Cross-Stream Trace Joiner and Flight Recorder

<!-- SCOPE: OS -->

**Status**: Proposed  
**Date**: 2026-05-06  
**Related**: ADR-033, ADR-086, ADR-190, ADR-193, ADR-196, ADR-201  
**Source**: `.cognitive-os/strategy/research/04-telemetry-action-gap.md`, `.cognitive-os/strategy/research/08-self-improvement-roadmap.md`

---

## Context

The telemetry research found 132 metric streams, roughly 64% firehose, and no
real cross-stream joiner despite ADR-033 correlation ids. Hook timing, ACI
observations, agent trajectory, skill suggestions, action receipts, cost events,
and state-retention events exist, but a service operator cannot reconstruct a
single run as prompt -> tool actions -> outcomes -> reward.

ADR-201's performance ledger depends on this joiner. Without a flight recorder,
the maintainer agent reads disconnected firehoses.

## Decision

Add a canonical **Run Flight Recorder** and cross-stream joiner.

Each run/session produces a joined trace with:

- `run_id`;
- `session_id`;
- `audit_id` / `change_id` where present;
- agent id and harness;
- primitive/tool events;
- timing/cost;
- action receipts;
- private-content access refs, not raw private content;
- verification outcomes;
- reward-signal refs;
- final status.

The joiner is a deterministic library, not an LLM. It reads existing JSONL
streams, validates correlation ids, and writes a bounded joined trace.

## Storage

- Joined traces: `.cognitive-os/runs/<run_id>/trace.json`.
- Summary index: `.cognitive-os/metrics/run-trace.jsonl`.
- Service API later: `GET /v1/runs/{run_id}/trace`.

Phoenix/OpenTelemetry may visualize traces, but local trace JSON remains the
source of truth for OSS mode.

## Consequences

### Positive

- Operators can inspect autonomous/service-mode decisions.
- ADR-201 ledger has correlated input.
- Firehose telemetry becomes queryable evidence.

### Negative / trade-offs

- Requires correlation discipline across writers.
- Historical streams without ids will be partially joinable only.
- Adds retention requirements for run traces.

## Implementation slices

1. Add `lib/trace_joiner.py`.
2. Add `scripts/cos-run-trace` and `scripts/cos observe run` route.
3. Join at least: agent trajectory, hook timing, skill suggestion, action
   receipts, cost events, state-retention audit, reward signals.
4. Add retention policy for `.cognitive-os/runs/`.
5. Add cosd/headless smoke proving a run trace is emitted.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_trace_joiner.py -q
python3 -m pytest tests/behavior/test_run_flight_recorder.py -q
scripts/cos-run-trace --session-id fixture-session --json
```

The behavior test must prove a run can be reconstructed without reading private
content payloads directly.
