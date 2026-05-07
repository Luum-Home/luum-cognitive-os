# ADR-226 — Event-Sourced Session Bus

<!-- SCOPE: OS -->

**Status**: Proposed
**Date**: 2026-05-06
**Related**: ADR-027 (session_bus baseline), ADR-099 (pre-agent snapshot), ADR-200 (state retention controller), ADR-220 (worktree divergence audit), ADR-221 (stash refs by SHA), ADR-222 (two-phase capture); load-bearing for ADR-227 (shadow-git), ADR-228 (retry+budget), ADR-230 (handoff), ADR-233 (cross-session agent teams)
**Source**: Synthesis of 11 orchestration-gap research reports (`docs/research/orchestration-gaps/`). The replay-timeline, retry-classifier, cost-ledger, and cross-session agent-team gaps all share the same prerequisite: an *event-sourced* session bus, not the *event-log* the OS has today.

---

## Context

`session_bus.py` (ADR-027 baseline) appends events to JSONL streams. It has the right shape — append-only, typed taxonomy, file-backed — but it is an **event log**, not an **event store**. The distinction matters because every downstream gap-closing primitive needs three properties the log does not provide:

1. **Monotonic sequence numbers per session** — without these, gap detection ("did we lose event 47?"), replay-from-position ("show me all events since seq 1023"), and idempotent processing ("apply this event only if seq > my last_processed") are impossible.
2. **Per-session event streams** — under concurrent agent sessions, all writes contend for one global file. Per-session streams isolate writers and let projections key off `session_id`.
3. **Memoized step recording** — non-deterministic LLM calls cannot be replayed. The Temporal/Inngest pattern is to record the *result* of an LLM call as an event on first execution and inject the stored result during replay rather than re-invoking the model. Without this, replay (ADR-227) is impossible for any session that includes an LLM call — i.e., every session.

Five separate research reports identified this same primitive as a prerequisite:
- Replay timeline ([`replay-timeline-architectures.md`](../research/orchestration-gaps/replay-timeline-architectures.md))
- Failure recovery ([`failure-recovery-retry-semantics.md`](../research/orchestration-gaps/failure-recovery-retry-semantics.md)) — needs sequence numbers for retry-after-position
- Cost-aware routing ([`cost-aware-routing.md`](../research/orchestration-gaps/cost-aware-routing.md)) — needs per-session streams for budget reconciliation
- Cross-session agent teams ([`cross-session-agent-teams.md`](../research/orchestration-gaps/cross-session-agent-teams.md)) — needs per-session streams as the IPC carrier
- Event-driven state ([`event-driven-orchestrator-state.md`](../research/orchestration-gaps/event-driven-orchestrator-state.md)) — direct prescription

OpenCode's `SyncEvent` and Temporal's `WorkflowEventHistory` are the production-validated reference shapes. Both are open-source, both share the same three primitives. We adopt the *pattern*, not the implementations — see C1 in [`orchestration-coverage-gap-analysis-2026-05-06.md`](../research/orchestration-coverage-gap-analysis-2026-05-06.md).

This ADR is **load-bearing for the Phase-1 substrate**. It must land before ADR-227, ADR-228, and ADR-233 because they all consume its shape. ADR-230 (handoff envelope) is independent but benefits from per-session streams as the natural carrier for envelope deltas.

## Decision

Upgrade `session_bus.py` from event-log to event-store with three additive primitives:

1. **Monotonic sequence numbers**: every `append_event()` allocates and persists a per-session monotonic `seq` (uint64). Allocation is atomic via `flock` on a per-session counter file; the counter is recovered on startup by reading the highest `seq` in the stream.
2. **Per-session streams**: events route to `.cognitive-os/sessions/{session_id}.events.jsonl`. The existing global log becomes a fan-out *index* (`.cognitive-os/coordination/event-index.jsonl`) carrying only `{seq, session_id, event_type, ts}` for cross-session projections.
3. **`@event_wrap` decorator**: wraps any function whose output is non-deterministic (LLM call, network call, time-dependent). On first execution, runs the function and persists the result as an event with `kind: "wrapped_step"`. On subsequent execution within a replay context (signalled by env var `COS_REPLAY_FROM_SEQ`), reads the stored result instead of re-invoking. Idempotency keyed on `(session_id, function_qualname, call_index_within_session)`.

## Manifest declaration

```yaml
# manifests/event-sourced-session-bus.yaml
schema_version: event-sourced-session-bus/v1
status: active
owner: platform-orchestration

streams:
  per_session_path: ".cognitive-os/sessions/{session_id}.events.jsonl"
  global_index_path: ".cognitive-os/coordination/event-index.jsonl"
  counter_dir: ".cognitive-os/sessions/.seq-counters/"

event_envelope_v2:
  required_fields:
    - schema_version       # "event-sourced-session-bus/v1"
    - seq                  # uint64 monotonic per-session
    - session_id
    - event_type
    - ts                   # ISO-8601 UTC
    - producer             # "orchestrator" | "subagent:<id>" | "hook:<name>"
  optional_fields:
    - payload              # event-type-specific
    - parent_seq           # causality link for derived events
    - wrapped_step         # set by @event_wrap; carries function_qualname + call_index + result_sha
    - file_tree_sha        # set by ADR-227 shadow-git after a tool call
    - cost_event           # set by ADR-228 dispatch wrapper

replay:
  env_signal: "COS_REPLAY_FROM_SEQ"
  required_artefacts:
    - per_session_stream
  refusal_conditions:
    - missing_session_stream
    - seq_gap_detected
    - schema_version_mismatch
    - wrapped_step_function_signature_changed   # detected via function_qualname; refuse rather than silently mis-replay

projection:
  built_in:
    - cost_ledger          # consumed by ADR-228
    - retry_classifier     # consumed by ADR-228
    - timeline             # consumed by ADR-227
    - handoff_chain        # consumed by ADR-230
  registration:
    location: "lib/event_projections/"
    interface: "fold(state, event) -> state"

migration:
  v1_legacy_log_path: ".cognitive-os/sessions/events.jsonl"
  v1_legacy_reader_active_until: "one_release_cycle"
  v1_to_v2_sequencer: "scripts/migrate_event_log_to_v2.py"
```

## Hard rules

- **`seq` is per-session, monotonic, gap-free under normal operation.** Gap detection is the consumer's responsibility but the producer guarantees no skipped allocation under successful append.
- **Append failure does not consume a `seq`.** The counter advances only on successful fsync of the event line. If fsync fails, the counter is rolled back; the next append retries the same `seq`.
- **`@event_wrap` MUST refuse to replay if the wrapped function's qualname or signature has changed since recording.** Silent replay against a changed function is the entire class of "deterministic replay diverged" production bugs.
- **The global index is a *fan-out* projection, not a primary.** Recovery from a corrupted index reads the per-session streams and rebuilds. The reverse (recovering a session from the index) is not supported.
- **No external dependencies.** `flock` is POSIX; `fsync` is POSIX; everything else is the existing Python stdlib. Honors C2 (footprint discipline).
- **Schema-versioned.** Every event carries `schema_version: event-sourced-session-bus/v1`. Consumers MUST check.

## Test tier matrix (per C3)

T1 ✅ unit — sequence allocator, per-session router, `@event_wrap` decorator
T2 ✅ integration — write+read+replay round-trip on fixture session
T3 ✅ behavior — manifest validator, schema rejection, refusal conditions
T4 ✅ smoke — end-to-end record→replay produces byte-identical projection state in <60s
T5 ✅ adversarial — `seq` gap injection, fsync failure mid-append, function signature change between record and replay, concurrent appends from N writers
T6 ✅ performance — append latency p50/p95/p99 under N=100 concurrent sessions; budget: p95 < 5ms
T7 ✅ chaos — kill -9 mid-append, full disk, corrupted index, missing session stream
T8 ⬜ cross-harness — N/A, internal substrate
T9 ⬜ adoption-truth — N/A, no external tool adopted
T10 ✅ audit invariants — append never mutates anything outside the stream + counter; verified by snapshot-equality test

## Consequences

### Positive

- **Five Phase-1 ADRs (227, 228, 230, 233 plus this) become implementable** without each defining its own event shape.
- **Replay determinism becomes possible** for any session whose LLM calls are wrapped — without VM snapshots or hypervisors. Closes Devin-parity gap at zero infra cost.
- **Per-session isolation eliminates write contention** under concurrent agents — directly addresses the production failure mode the prior-art research documented.
- **Projections become first-class.** Cost ledger, retry classifier, timeline, handoff chain all reduce to `fold(state, event)` consumers.
- **Schema versioning enables the next migration without a stop-the-world**: v3 will be additive over v2 like v2 is over v1.

### Negative / trade-offs

- **One-release-cycle of dual-format support** during v1→v2 migration. Mitigation: `v1_legacy_reader_active_until` is explicit; sequencer script provides offline migration path; tests cover both paths.
- **Per-session files multiply inode count** under high session churn. Mitigation: ADR-200 retention controller already governs session lifecycle; per-session streams are deleted with the session.
- **`@event_wrap` requires careful function authorship** — wrapping a non-pure function and expecting deterministic replay breaks. Mitigation: hard-rule refusal on signature change; documentation example showing the contract.
- **The global index becomes a hot-write file under N concurrent sessions** — even though it carries minimal payload. Mitigation: index is best-effort; primary is per-session stream; index can be rebuilt offline.

## Alternatives rejected

- **Adopt Temporal directly.** Apache 2.0 (allowlist) but mandatory server, mandatory cluster, multi-GB image. Violates C2 in every consumer surface. Pattern adoption only.
- **Adopt Inngest.** Apache 2.0 OK; SaaS-first, self-host requires Postgres + Redis. Violates C2 default-no-external-database.
- **Use SQLite as event store.** Tempting; SQLite is in stdlib. Rejected because per-session JSONL is human-readable, simpler to back up, easier to rebuild from, and trivially inspectable. SQLite as a *projection cache* is a Phase-2 option, not the primary store.
- **Single global stream with `session_id` as a field.** This is what we have today and is exactly what creates the contention problem. Rejected.
- **Replace `session_bus.py` rather than extend.** Considered; the existing v1 readers are baked into 14+ consumers. Additive v2 with one-release-cycle legacy reader is lower risk.
- **Push `@event_wrap` semantics into the LLM dispatch layer (`lib/dispatch.py`) only.** Considered; would miss network calls, time-dependent operations, file reads. The decorator is general enough to be the right primitive.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_event_sourced_bus.py tests/behavior/test_replay_round_trip.py tests/audit/test_event_schema_v2.py tests/perf/test_event_append_latency.py -q

# Smoke (T4): record a 30-event session, kill the process, restart, replay from seq 0, assert byte-identical projection state
bash tests/smoke/test_event_record_replay.sh

# Chaos (T7): kill -9 during append, assert no stream corruption and no skipped seq
bash tests/chaos/test_event_append_kill9.sh
```

The tests must prove:

- `append_event()` allocates monotonically increasing `seq` even under N=10 concurrent producers.
- A killed-mid-append leaves the stream readable; the next append retries the same `seq`.
- `@event_wrap` records the result on first call and returns it from storage on second call within `COS_REPLAY_FROM_SEQ` context.
- `@event_wrap` refuses to replay when wrapped function's qualname or signature has changed.
- Per-session stream + global index are consistent: every event in a session stream has exactly one matching index entry.
- `seq` gap in a stream raises `EventStreamGapDetected` on first read.
- v1 legacy events are read by the v1-legacy reader; new events are written in v2.
- Append latency p95 < 5ms under N=100 concurrent sessions on a 7200-rpm disk fixture.

## Implementation slices

Each slice is independently shippable; later slices depend on earlier ones.

1. **Slice A — Sequence allocator + per-session streams** (~60 LOC). `lib/session_bus.py` v2: add `seq` allocator with `flock`-protected counter; route `append_event()` by `session_id`. Maintain v1 readers. Tests T1+T3+T7+T10.
2. **Slice B — Fan-out global index** (~30 LOC). Background thread or hook tap that mirrors `{seq, session_id, event_type, ts}` to `.cognitive-os/coordination/event-index.jsonl`. Tests T2+T5.
3. **Slice C — `@event_wrap` decorator** (~50 LOC). `lib/event_wrap.py`. Records on first call, replays under env signal. Hard-rule refusal on signature mismatch. Tests T1+T2+T5.
4. **Slice D — Migration tool** (~30 LOC). `scripts/migrate_event_log_to_v2.py`. Reads v1 global log, demultiplexes by `session_id`, allocates seq numbers, writes per-session streams. Idempotent. Tests T3+T4.
5. **Slice E — Built-in projections** (cost ledger, retry classifier, timeline, handoff chain stubs). `lib/event_projections/*.py`. Each is `fold(state, event) -> state`. Will be wired by ADRs 227/228/230. Tests T2.

Total: ~170 LOC for the substrate. ADR-227/228/230 will add their own consumer code on top.

## Open questions

- **Should the global index be an SQLite db rather than JSONL?** Defer. JSONL keeps the rebuild story simple. Revisit if cross-session projection performance becomes a bottleneck.
- **Should `@event_wrap` support partial replay (replay first N wrapped calls, re-execute the rest)?** Defer. MVP is replay-all-or-replay-none. Partial replay is a Phase-3 addition once we have a use case.
- **Should we expose `seq` to MCP consumers (ADR-231) so external tools can subscribe to a session's stream?** Likely yes — this is how MCP becomes the natural bus for cross-session agent-teams (ADR-233). Tracked as a slice of ADR-231.
- **Counter-file recovery on a corrupted directory.** Initial answer: walk the stream, take `max(seq) + 1`. If the stream is also corrupted, refuse and require operator intervention (no silent re-allocation).
