---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-028b.md
adr: ADR-028b
status: accepted
reality_level: REAL
provenance: ADR-028 D1.C's original implementation (commit 3d03419, reverted in 8eb57b2) built a parallel heartbeat system writing `.cognitive-os/tasks/{agent_id}.heartbeat` files every 60s — duplicating `lib/agent_bus.py`, which already published heartbeats every 5s via `AgentPublisher.start_heartbeat_thread()` with Valkey pub/sub and JSONL fallback, because the ADR was written against a mental model of the codebase instead of a discovery pass over actual files.
---

## Decision
Do not recreate the reverted artifacts (`lib/agent_heartbeat.py`, `hooks/_lib/heartbeat.sh`, `.cognitive-os/tasks/{agent_id}.heartbeat`). Instead, build a thin adapter `lib/agent_bus_metrics.py` (`AgentBusMetrics`) that bridges `agent_bus` heartbeats to durable `MetricEvent` JSONL records: emits `agent_launched` on first heartbeat from an unseen agent, `agent_completed` when `alive=False`, provides `scan_stale()` for cross-session-boundary stale-agent detection, `list_live()`, and `mark_hung_and_publish()` to mark+signal-stop a hung agent. Also add `scripts/so-agent-status.sh` (CLI listing live agents from the adapter) and wire `scripts/so-vitals.sh`'s hard-coded zero agent-count to call `list_live()`.

## Why
`agent_bus.py` already provided heartbeat transport (5s cadence, Valkey pub/sub with JSONL fallback), progress/control channels, and in-memory last-heartbeat tracking via `OrchestratorSubscriber`. What it did NOT provide, and what D1.C actually needed: durable offline `MetricEvent` records (agent_bus publishes real-time only, no JSONL trend history for watchdog tooling), stale-heartbeat detection across session boundaries (in-memory state is transient), and `so-vitals.sh` agent-count integration (it reported 0 agents in flight with no code path to count them). This is the second ADR-028 scope error caught before execution — the first was ADR-028a §5.1's corrected `~40%` unparseable hook-health claim (actual: 0 bad rows).

## Consequences
Positive: avoids duplicating existing heartbeat transport; provides the actually-missing durable-metrics and stale-detection layer on top of existing infrastructure; corrects `so-vitals.sh`'s permanently-zero agent count with one function-call swap, no structural change. The addendum also formalizes a mitigation going forward: every ADR section introducing new infrastructure must include a "Discovery pass" subsection listing existing files found by grep/Glob before defining new artifacts — sections without one are incomplete and must be revised before execution.

## Status & current state
Implemented (per frontmatter). Action items were tracked as a checklist: create `lib/agent_bus_metrics.py` per the API contract, update `so-vitals.sh`'s agent-count path, mark the original ADR-028 D1.C text as superseded, update ADR-028a §2's consumer-boundary table to reference the correct FallbackBus path, and verify ADR-028 D1.A.0 (fixed MetricEvent write path) lands before D1.C executes, since the JSONL sink depends on it.

## Key links
- ADR-028 (parent) — D1.C original spec (lines 166-214) is superseded by this addendum
- ADR-028a §2 — consumer-boundary table amended to reference `.cognitive-os/agent-bus/{agent_id}/heartbeat.jsonl` instead of the deprecated `.cognitive-os/tasks/{agent_id}.heartbeat`
- `lib/agent_bus.py` — existing heartbeat/pub-sub infrastructure this ADR builds on top of, not around
- `lib/claude_executor.py` (line 267), `lib/agent_dashboard.py` (line 201-202) — existing consumers, unchanged
