---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-226-event-sourced-session-bus.md
adr: ADR-226
status: accepted
reality_level: REAL
provenance: session_bus.py (ADR-027 baseline) was an append-only event log, not an event store — it lacked per-session monotonic sequence numbers, per-session streams (all writes contended for one global file under concurrent agents), and memoized non-deterministic step recording, blocking replay, gap-detection, and idempotent processing that 5 of the 11 orchestration-gap research reports synthesized into this ADR independently identified as the same missing prerequisite.
---

## Decision

Extend the ADR-205 Flight Recorder substrate with three additive, opt-in primitives on top of the existing `session_bus.append_event()` API: (1) monotonic per-session sequence numbers with atomic allocation and stream-is-truth/counter-is-cache recovery; (2) per-session event streams at `.cognitive-os/sessions/{session_id}.events.jsonl`, with the prior global flight-recorder log demoted to a fan-out index projection; (3) an `@event_wrap` decorator that persists non-deterministic function results (LLM calls, network calls) as events on first execution and replays the stored result under `COS_REPLAY_FROM_SEQ` instead of re-invoking.

## Why

Without monotonic per-session sequencing, gap detection ("did we lose event 47?"), replay-from-position, and idempotent processing are all impossible. Under concurrent agent sessions a single global stream forces every writer to contend for one file. And non-deterministic LLM calls cannot be replayed at all without recording their result on first execution — without this primitive, replay (ADR-227) is impossible for literally every session, since every session includes at least one LLM call. Five independent research reports (replay-timeline, failure-recovery-retry-semantics, cost-aware-routing, cross-session-agent-teams, event-driven-orchestrator-state) each converged on the same missing prerequisite. The original draft's implicit "fsync every event, p95 <5ms" claim was corrected mid-ADR to a measured, tunable group-commit model (default N=8 events or T=100ms, whichever first) after being judged unsupportable without measurement on typical filesystems/hardware.

## Consequences

Positive: five downstream Phase-1 ADRs (227 shadow-git, 228 retry+budget, 230 handoff, 233 cross-session agent teams, plus this one) become implementable against a stable shape instead of each inventing its own event format; replay determinism becomes possible for any session with wrapped LLM calls, at zero infrastructure cost (no VM snapshots/hypervisors); per-session isolation eliminates the write-contention failure mode the research documented; cost ledger, retry classifier, timeline, and handoff-chain projections all reduce to a uniform `fold(state, event) -> state` interface.

Negative/trade-offs: one release cycle of dual v1/v2 format support during migration; per-session files multiply inode count under high session churn (mitigated — ADR-200 retention controller deletes streams with the session); `@event_wrap` requires careful function authorship since wrapping a non-pure function breaks replay silently unless the hard rule (refuse on signature/qualname change) catches it; the global index becomes a hot-write file under many concurrent sessions, mitigated by treating it as best-effort/rebuildable, never the primary. Locking uses POSIX `flock`, which explicitly refuses to advance on NFS/FUSE without an opt-in flag and is unsupported by default on Windows.

## Status & current state

Accepted, implemented through Slice E (2026-05-07). All five slices shipped: Slice A (sequence allocator + per-session stream writer + gap-detecting reader + baseline latency measurement, no budget asserted), Slice B (fan-out global index + an initial conservative p95 budget of 25ms recorded in the manifest, flagged as needing revisit after a real concurrent benchmark), Slice C (`lib/event_wrap.py`, JSON-serializable results only, refuses replay on signature mismatch), Slice D (`scripts/migrate_event_log_to_v2.py`, idempotent v1-to-v2 migration), Slice E (`lib/event_projections/` stubs for cost ledger, retry classifier, timeline, handoff chain). Focused T1-T6/T10 test suites passed locally at ADR acceptance time. `partial_remaining` in frontmatter is stale relative to the body's "implemented" log — it lists fan-out index/`@event_wrap`/migration/projections as excluded from Slice A specifically, but all were completed in the later slices per the same document.

## Key links

ADR-205 (Flight Recorder — the substrate this ADR extends, retains ownership of cross-stream trace joining), ADR-027 (session_bus.py baseline), ADR-227 (shadow-git, consumes this substrate), ADR-228 (retry+budget ledger), ADR-230 (handoff envelope), ADR-233 (cross-session agent teams), `manifests/event-sourced-session-bus.yaml` (schema/durability/locking/replay contract), `manifests/orchestration-research-evaluation.yaml` (C1-C4 evaluation contract), `docs/03-PoCs/research/orchestration-gaps/` (source research reports).
