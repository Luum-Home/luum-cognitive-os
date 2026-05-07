# ADR-226 — Event-Sourced Session Bus

<!-- SCOPE: OS -->

**Status**: Accepted — Slice A implemented (2026-05-07)
**Date**: 2026-05-06
**Extends**: **ADR-205 (Cross-Stream Trace Joiner and Flight Recorder)** — ADR-226 is an *extension* of the Flight Recorder's append-only event substrate, not a replacement. ADR-205 keeps owning cross-stream trace joining and the flight-recorder retention story; ADR-226 adds three primitives (per-session sequencing, per-session streams, memoized step wrapping) on top of that substrate.
**Related**: ADR-027 (session_bus baseline), ADR-099 (pre-agent snapshot), ADR-200 (state retention controller), ADR-220 (worktree divergence audit), ADR-221 (stash refs by SHA), ADR-222 (two-phase capture); load-bearing for ADR-227 (shadow-git), ADR-228 (retry+budget), ADR-230 (handoff), ADR-233 (cross-session agent teams)
**Source**: Synthesis of 11 orchestration-gap research reports (`docs/research/orchestration-gaps/`). The replay-timeline, retry-classifier, cost-ledger, and cross-session agent-team gaps all share the same prerequisite: per-session sequencing + memoized step wrapping on top of the existing flight recorder.
**Evaluation contract**: [`manifests/orchestration-research-evaluation.yaml`](../../manifests/orchestration-research-evaluation.yaml) — C1/C2/C3/C4.

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

Extend the ADR-205 Flight Recorder substrate with three additive primitives, all opt-in via the existing `session_bus.append_event()` API:

1. **Monotonic per-session sequence numbers**: every `append_event()` allocates and persists a per-session monotonic `seq` (uint64). Allocation is atomic via a per-session counter; recovery on startup walks the stream to find `max(seq)`. The counter file is the *cache*; the stream is the *truth*. See §"Atomicity model" below for the durability contract.
2. **Per-session streams**: events route to `.cognitive-os/sessions/{session_id}.events.jsonl`. The existing ADR-205 flight-recorder global log continues to receive a fan-out *index* (`{seq, session_id, event_type, ts}` only) for cross-stream joining. Per-session streams are the primary; the global index is a projection.
3. **`@event_wrap` decorator**: wraps any function whose output is non-deterministic (LLM call, network call, time-dependent). On first execution, runs the function and persists the result as an event with `kind: "wrapped_step"`. On subsequent execution within a replay context (signalled by env var `COS_REPLAY_FROM_SEQ`), reads the stored result instead of re-invoking. Idempotency keyed on `(session_id, function_qualname, call_index_within_session)`.

## Atomicity model (replaces the simplified "fsync per event" claim)

The original draft asserted "append latency p95 < 5ms" with implicit per-event fsync. That budget is unsupportable on most filesystems and operator hardware without measurement. The corrected contract:

- **Default mode — group commit.** Events are written via `write()` and become durable on the next `fsync()`, which is triggered every N events or every T milliseconds (whichever comes first; defaults `N=8`, `T=100ms`, both manifest-tunable). Crash semantics: at most N–1 events may be lost on power-fail; no event is partially-written (the writer holds the per-session lock for the duration of a `write()`).
- **Strict mode — per-event fsync.** Opt-in via `event_bus.strict_durability=true`. Every `append_event()` fsyncs before returning. Used when the event itself is the audit record of a destructive operation (e.g. ADR-227 file restore commit, ADR-228 idempotency-key claim).
- **Sequence rollback on append failure.** The counter advances *after* successful `write()`. On `write()` exception, the counter is rolled back; the next append reuses the same `seq`. On `fsync()` exception (group-commit failure), the affected events are re-written to a quarantine stream and the operator is notified — they are not silently lost.
- **Recovery contract.** On process restart, `recover_session(session_id)` walks the stream, takes `max(seq)`, and validates the stream is gap-free up to that point. Gaps trigger refusal to append and an operator alert. The stream is the source of truth; the counter file is rebuildable from the stream.

Performance budgets are **measured first** (per C3 and the evaluation manifest's T6 caveat). Slice A delivers a baseline measurement; subsequent slices propose budgets grounded in that measurement.

## Locking and portability

`flock(2)` is the portable POSIX advisory lock primitive. ADR-226 uses it as the default per-session counter lock. Portability constraints:

- **Linux**: `flock(2)` works on local filesystems. **Refuses to advance the counter on NFS / FUSE** unless the operator opts in via `event_bus.allow_network_fs=true` — `flock` semantics on NFS are implementation-defined and have produced historical data loss.
- **macOS**: `flock(2)` is supported. APFS is the supported default. Network volumes inherit the same opt-in guard as Linux NFS.
- **Windows**: not a supported default. ADR-226 emits an explicit `unsupported_platform` error on Windows. A future slice may add `msvcrt.locking()` support behind an opt-in flag, but Windows is outside the local-first default scope.
- **Other harnesses**: harnesses running COS in environments without `flock` (containers without `/var/lock`, restricted sandboxes) can opt into a *single-writer mode* (`event_bus.single_writer=true`) that skips locking entirely. This is safe iff the operator guarantees one process per session — appropriate for ADR-211 service-mode where the dispatcher already enforces that.

The portability matrix is declared in the manifest below and verified by T8 cross-harness tests.

## Manifest declaration

```yaml
# manifests/event-sourced-session-bus.yaml
schema_version: event-sourced-session-bus/v1
status: active
owner: platform-orchestration
extends: "ADR-205 Flight Recorder"

streams:
  per_session_path: ".cognitive-os/sessions/{session_id}.events.jsonl"
  global_index_path: ".cognitive-os/coordination/event-index.jsonl"   # ADR-205 flight-recorder index, extended with seq
  counter_dir: ".cognitive-os/sessions/.seq-counters/"

durability:
  default_mode: "group_commit"
  group_commit_n: 8           # fsync every N events
  group_commit_t_ms: 100      # or every T ms
  strict_mode_opt_in: "event_bus.strict_durability=true"
  strict_mode_required_for:
    - "ADR-227 file_restore_committed"
    - "ADR-228 idempotency_key_claimed"
    - "operator_destructive_action"

locking:
  primitive: "flock(2)"
  supported_platforms: ["linux+local_fs", "darwin+apfs"]
  refuses_on_default:
    - "linux+nfs"            # opt in via allow_network_fs=true
    - "linux+fuse"
    - "darwin+network_volume"
    - "windows"              # explicit unsupported_platform error
  single_writer_escape_hatch:
    flag: "event_bus.single_writer=true"
    safe_when: "operator guarantees one process per session (ADR-211 service mode)"

performance:
  budgets_set_after_measurement: true
  slice_a_baseline_required: true
  initial_target: "p95 measurable; budget proposed in Slice B"

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
- **Append failure does not consume a `seq`.** In Slice A the counter cache advances only after a successful stream write. In strict durability mode, `fsync()` is part of the success condition; in default group-commit mode, durability is intentionally amortized per §"Atomicity model". The stream remains the source of truth and the counter is rebuildable.
- **`@event_wrap` MUST refuse to replay if the wrapped function's qualname or signature has changed since recording.** Silent replay against a changed function is the entire class of "deterministic replay diverged" production bugs.
- **The global index is a *fan-out* projection, not a primary.** Recovery from a corrupted index reads the per-session streams and rebuilds. The reverse (recovering a session from the index) is not supported.
- **No external dependencies.** `flock` is POSIX; `fsync` is POSIX; everything else is the existing Python stdlib. Honors C2 (footprint discipline). Locking-platform constraints declared in §"Locking and portability" and the manifest's `locking.supported_platforms`.
- **Schema-versioned.** Every event carries `schema_version: event-sourced-session-bus/v1`. Consumers MUST check.

## Test tier matrix (per C3)

T1 ✅ unit — sequence allocator, per-session router, `@event_wrap` decorator
T2 ✅ integration — write+read+replay round-trip on fixture session
T3 ✅ behavior — manifest validator, schema rejection, refusal conditions
T4 ✅ smoke — end-to-end record→replay produces byte-identical projection state in <60s
T5 ✅ adversarial — `seq` gap injection, fsync failure mid-append, function signature change between record and replay, concurrent appends from N writers
T6 ✅ performance — append latency p50/p95/p99 under N=100 concurrent sessions. **Slice A delivers the baseline measurement on operator hardware; the budget is proposed in Slice B based on that data.** No upfront p95 number asserted — per the evaluation manifest's T6 caveat.
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
- Slice A records a local latency baseline without asserting a p95 budget; Slice B proposes the budget from measured data.

## Implementation slices

Each slice is independently shippable; later slices depend on earlier ones. **LOC numbers are agent-reported estimates** — treat as direction, not commitment.

### Slice A — Minimum viable substrate (lands first, alone)

Scope reduced from the original draft. The goal of Slice A is to validate the *shape* against operator hardware before any consumer (ADR-227 / 228 / 230 / 233) drafts against it.

Includes:
- **Sequence allocator** with `flock`-protected per-session counter (Linux+local_fs, macOS+APFS only — refusal on NFS/FUSE/Windows).
- **Per-session stream writer** at `.cognitive-os/sessions/{session_id}.events.jsonl` with the durability contract from §"Atomicity model" (group commit by default; strict mode opt-in).
- **Stream reader with gap detection** (`read_session(session_id) -> Iterator[Event]`; raises `EventStreamGapDetected` on the first gap).
- **Smoke test (T4)**: end-to-end record N events, kill the process, restart, replay from seq 0, assert byte-identical projection state. <60s.
- **Baseline performance measurement (T6)**: report p50/p95/p99 append latency on operator hardware. No budget asserted; the report becomes input to Slice B's budget proposal.
- **Tests**: T1 (allocator unit), T3 (manifest validator), T4 (smoke), T7 (kill mid-append, fsync failure), T10 (read-only audit invariants).

Excludes (deferred to later slices): fan-out global index, `@event_wrap` decorator, migration tool, projections.

### Slice B — Fan-out global index + perf budget

After Slice A's baseline measurement lands.
- Mirror `{seq, session_id, event_type, ts}` to `.cognitive-os/coordination/event-index.jsonl` (extends the ADR-205 flight-recorder index).
- Propose a p95 append-latency budget grounded in Slice A's measurements; lock the budget into the manifest.
- Tests T2 (cross-stream consistency), T5 (concurrent writer contention on the index).

### Slice C — `@event_wrap` decorator

After Slice B. The piece replay actually depends on.
- `lib/event_wrap.py`. Records on first call, replays under env signal. Hard-rule refusal on signature mismatch.
- Tests T1, T2, T5.

### Slice D — Migration tool

After Slice C.
- `scripts/migrate_event_log_to_v2.py`. Reads v1 ADR-205 flight-recorder log, demultiplexes by `session_id`, allocates seq, writes per-session streams. Idempotent.
- Tests T3, T4 (round-trip migration smoke).

### Slice E — Built-in projection stubs

After Slice C, before consumer ADRs draft against the substrate.
- `lib/event_projections/*.py` for cost ledger, retry classifier, timeline, handoff chain. Each is `fold(state, event) -> state`. Stubs only; consumer ADRs (227/228/230) wire them.
- Tests T2.

**Critical sequencing rule**: no consumer ADR drafts code against Slice C+ shape until Slice A baseline + Slice B budget are committed and reviewed. This is the single piece of discipline that prevents the substrate from being prematurely locked in to the wrong shape.

## Implementation status

- **2026-05-07 — Slice A implemented**: `lib/session_bus.py` now exposes `append_session_event()`, `read_session_events()`, `recover_session_counter()`, and an `append_event(..., event_store=True)` opt-in path. The slice writes `.cognitive-os/sessions/{session_id}.events.jsonl`, maintains rebuildable `.seq-counters/{session_id}.counter`, rejects unsafe session IDs, refuses unsupported filesystem/platform paths, and provides gap-detecting reads.
- **Manifest**: `manifests/event-sourced-session-bus.yaml` declares the Slice A active contract and defers fan-out index, `@event_wrap`, migration, and projections.
- **Validation**: focused T1/T3/T4/T6/T10 tests passed locally: `python3 -m pytest tests/unit/test_event_sourced_bus.py tests/behavior/test_event_sourced_bus_smoke.py tests/audit/test_event_sourced_bus_invariants.py tests/benchmark/test_event_sourced_bus_baseline.py tests/unit/test_cross_session_events.py tests/contracts/test_cross_session_event_taxonomy.py -q` → 25 passed; `bash -n hooks/*.sh` passed.

## Open questions

- **Should the global index be an SQLite db rather than JSONL?** Defer. JSONL keeps the rebuild story simple. Revisit if cross-session projection performance becomes a bottleneck.
- **Should `@event_wrap` support partial replay (replay first N wrapped calls, re-execute the rest)?** Defer. MVP is replay-all-or-replay-none. Partial replay is a Phase-3 addition once we have a use case.
- **Should we expose `seq` to MCP consumers (ADR-231) so external tools can subscribe to a session's stream?** Likely yes — this is how MCP becomes the natural bus for cross-session agent-teams (ADR-233). Tracked as a slice of ADR-231.
- **Counter-file recovery on a corrupted directory.** Initial answer: walk the stream, take `max(seq) + 1`. If the stream is also corrupted, refuse and require operator intervention (no silent re-allocation).
