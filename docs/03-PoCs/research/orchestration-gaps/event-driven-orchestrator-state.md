# Event-Driven Orchestrator State: Patterns Map and session_bus Evolution

**Status**: Research — no code changes
**Date**: 2026-05-06
**Scope**: Event sourcing patterns for agent orchestrators; COS gap analysis relative to field state
**Companion**: `docs/03-PoCs/research/orchestration-coverage-gap-analysis-2026-05-06.md` — identifies streaming/replay as a partial-coverage gap

---

## Executive Summary

COS's `session_bus.py` is an append-only coordination log. It records 12 event types, enforces an ADR-183 taxonomy, and provides peer-session discovery. What it does not do: (1) reconstruct orchestrator state from the event log alone, (2) support deterministic replay for failure recovery, (3) project read models from event streams, or (4) serve as the source of truth that all other state derives from. The field has converged on end-to-end event-sourced orchestrators — OpenCode's SyncEvent system, Temporal's durable event history, LangGraph's checkpoint-backed StateGraph, and Inngest's step memoization — that satisfy all four properties. This report maps those patterns, identifies what replay determinism implies for COS, and recommends a concrete evolution path.

---

## 1. The Theoretical Foundation: Event Sourcing vs. State Machines

Traditional orchestrators represent agent state as a mutable record that transitions through a finite state machine. A transition function `T: Input × State → Output × State` updates the record in place. This approach breaks under partial failures because the write to persistent storage is not atomic with the decision to transition.

Event sourcing factors the transition into two deterministic pure functions (after Eugène Tolmachev's gist on the relationship between state machines and event sourcing):

```
exec  : Input  × State  → Output   # decide what happened
apply : Output × State  → State    # fold the event into new state
```

The key insight is that you never need to store `State` directly. Given an immutable, append-only log of `Output` values (events) and an initial state `S0`, current state is always recoverable via:

```
state = foldl apply S0 events
```

This is deterministic replay: the same event sequence always produces the same state. The `apply` function must be pure and idempotent. Because `exec` is separate, you can change business logic (a new version of `exec`) while replaying old events through `apply` to migrate state — a property no mutable-state machine provides.

Applied to orchestrators: every agent decision, LLM call result, tool execution, and coordination message becomes an event. State is derived, never stored directly. Replaying the log reconstructs any historical state and enables time-travel debugging.

---

## 2. Field Survey: How Production Systems Implement Event-Sourced Orchestration

### 2.1 Temporal / Cadence: The Event History Backbone

Temporal (and its predecessor Cadence, which powered Uber's microservices) builds its durable execution model on a complete event history. As Temporal's documentation states, the platform "records a full Event History — every single time code in the Workflow is run, every single time an Activity is called or returned." This history is stored in an external persistence layer (Cassandra, PostgreSQL, or MySQL) and is the sole source of truth for workflow state.

When a worker crashes, Temporal reconstructs application state by replaying the Event History against the workflow code. Workers "replay the Event History to reconstitute the application state for further processing." Developers never implement checkpointing; it is a structural property of the system.

For AI agents specifically, Temporal wraps each LLM invocation as an Activity — a durable step that records its result. If the LLM call fails (rate limit, network error, crash), the retry resumes from the last recorded Activity result, not from the beginning of the workflow. This prevents re-issuing expensive LLM tokens and ensures consistent outputs across retries.

The system also provides inter-agent coordination primitives that are event-sourced by construction: **Signals** (fire-and-forget events delivered to a running workflow) and **Queries** (read-only state inspection without interrupting execution). In the ambient-agent pattern, a judge agent sends Signals to update a running execution agent's system prompt, and the execution agent emits Queries back. All of this is recorded in the shared event history, eliminating the need for an external message bus between co-located agents.

Temporal's "very long-running workflows" capability — agents operating for weeks or months — is only possible because state reconstruction from event history is O(log n) in practice (Temporal uses periodic "history compaction" snapshots to bound replay cost).

**Key properties**: Complete event history, deterministic replay, LLM-call durability, inter-agent signals/queries as first-class events, no manual checkpointing required.

### 2.2 LangGraph: StateGraph Checkpointing and Time-Travel

LangGraph's orchestration model represents agent execution as a directed acyclic graph (with optional cycles for agentic loops). Each node processes a portion of a centralized `State` object and returns partial updates. The framework applies these updates immutably: "when an agent updates the state, a new version is created rather than altering the existing one."

LangGraph 1.0 (released October 2025) added production-ready checkpoint persistence via pluggable backends: `SqliteSaver`, `PostgresSaver`, and `DynamoDBSaver`. A checkpoint is saved after every node execution. This enables:

1. **Resume from failure**: On worker restart, the graph replays from the last checkpoint rather than from the start.
2. **Time-travel debugging**: Developers can roll back to any prior checkpoint and re-execute from that point, making the execution history browsable.
3. **Human-in-the-loop**: A workflow can pause at a node, persist the checkpoint, release the compute resource, and resume when an operator responds.

LangGraph also introduced streaming support that emits typed events as nodes execute: `on_chain_start`, `on_chain_end`, `on_tool_start`, `on_tool_end`, `on_llm_start`, `on_llm_end`. These streaming events serve two purposes: real-time UI updates and the event log that drives replay. The streaming model is built on Anthropic's SDK streaming infrastructure, which delivers incremental events containing text and tool-call fragments.

The StateGraph model is closer to database-checkpointing (snapshot after each node) than to pure event sourcing (fold over event log). This is a practical compromise: it is easier to implement and does not require developers to write pure `apply` functions. The tradeoff is that state cannot be reconstructed from the event log alone — you need both the checkpoints and the graph topology.

**Key properties**: Immutable state snapshots per node, pluggable checkpoint backends, time-travel via checkpoint rollback, streaming events for real-time observation, human-in-the-loop via checkpoint pause.

### 2.3 OpenCode (SST): SyncEvent and True Event Sourcing

OpenCode's session_bus is the closest analogue to what COS's `session_bus.py` aspires to be — and it demonstrates the gap clearly. OpenCode implements what it calls `SyncEvent`: an event-sourcing system where all mutations are recorded as versioned events before state is projected.

The flow for every state change is:

1. A `SyncEvent` (e.g., `Session.Event.Created`, `Message.Event.Added`) is created.
2. Associated **projectors** run: they update `SessionTable`, `MessageTable`, and `PartTable` in SQLite via Drizzle ORM.
3. The event is appended to `EventTable` with a monotonic sequence number.
4. If publishing is enabled, `GlobalBus` broadcasts the event to all SSE (Server-Sent Events) subscribers.

The sequence number provides a **linearization point**: events with sequence ≤ current are idempotent (ignored on replay), and events with sequence > current + 1 are rejected (gap detection). This is exactly the append-only + sequence-validation pattern required for correct event sourcing.

`SyncEvent.replay` allows a new subscriber (or a recovering subscriber) to catch up by reading `EventTable` from a given sequence number. This is not available in COS's `session_bus.py`, which only provides `read_events` with a `limit` parameter (tail-based, not sequence-based).

The `SessionEntryStepper` reconstructs live session views by reducing streams of `SessionEvent` objects into typed `SessionEntry` classes (User, Assistant, Synthetic, Compaction). This is a **projection** in CQRS terms: a read model derived by folding the event stream, not by reading mutable state directly.

OpenCode also separates **Instance-scoped events** (project-specific, via `Bus`) from **Global events** (cross-project, via `GlobalBus`). The separation enables multi-project coordination without routing confusion — a distinction absent from COS's single `events.jsonl` log.

**Key properties**: Fully event-sourced state (SyncEvent + projectors), monotonic sequence numbers, gap detection, replay from arbitrary sequence, read-model projections (SessionEntryStepper), Bus/GlobalBus scope separation, SSE streaming to clients.

### 2.4 Inngest: Step-Based Memoization (Pragmatic Durability)

Inngest's model is instructive for what "durable execution without strict event sourcing" looks like. Instead of replaying an event log, Inngest implements **step-based memoization**: each `step.run(...)` block executes once, persists its result externally, and on subsequent executions the SDK injects the stored result into the return value without re-running the code.

This is closer to "result caching" than to event sourcing. The key distinction: Inngest does not require deterministic workflows. Non-deterministic operations (random, current time, external API calls) are safe as long as they are inside `step.run` boundaries. Temporal requires determinism because it replays code against a history; Inngest never replays code — it skips completed steps entirely.

For AI agent workflows, Inngest's approach means:
- LLM calls inside `step.run` are memoized: retries use the cached response, not a new LLM invocation.
- Sub-agents are spawned via `step.invoke`, which creates an independently retriable function run with its own step history.
- `step.waitForEvent` blocks a workflow until an external event arrives, enabling event-driven orchestration across workflows.

Inngest's blog post "Your Agent Needs a Harness, Not a Framework" articulates the principle: agent frameworks that reinvent retry logic, state persistence, and job queues are solving infrastructure problems with application code. Durable, event-driven infrastructure — where step results persist automatically — is the correct abstraction layer.

The tradeoff: Inngest's step memoization does not provide a queryable event history. You cannot fold over the event log to reconstruct arbitrary historical state. It is a durability primitive, not a full event sourcing system.

**Key properties**: Step-based memoization (not replay), non-determinism safe within step boundaries, sub-agent spawning via step.invoke, event-triggered coordination across workflows, no queryable event history.

### 2.5 Restate: Journal-Based Lightweight Durability

Restate implements durable execution via **journaling**: every handler step is recorded in a journal, and on crash the handler resumes from its last journal position. The architecture is a "single self-contained binary" — no external database required for basic durability, unlike Temporal's persistence backend requirements.

Restate's **Virtual Objects** provide keyed, single-writer, consistent state: an ideal primitive for per-agent or per-resource state isolation. The combination of journaling + virtual objects enables the "virtual state machines that wake up, react to events, and then go back to sleep" pattern.

Restate opened Cloud publicly in 2025, with production use cases spanning AI workflows, crypto trading, and banking infrastructure. A notable integration is the Axon + Restate webinar demonstrating CQRS with event sourcing using durable execution: Axon provides the event store and CQRS structure; Restate provides the execution harness. This combination shows that event sourcing and durable execution are complementary, not competing, patterns.

**Key properties**: Journal-based replay, virtual objects for keyed state, single binary deployment, CQRS-compatible, lighter operational footprint than Temporal.

### 2.6 AWS Step Functions: Managed State Machines with Event History

AWS Step Functions represents the managed-cloud end of the spectrum. Each execution maintains a complete event history in CloudWatch, and individual states persist their output for the next state. The "Express Workflows" variant targets short-lived, high-throughput workflows; "Standard Workflows" target long-running, durable executions.

Step Functions does not provide deterministic replay in the Temporal sense (re-executing code against history). Instead, it snapshots state at each step transition. For agent orchestration, this means LLM calls must be wrapped as Lambda functions or Bedrock invocations, each of which becomes a named state with persisted input/output.

The integration with Amazon Bedrock AgentCore (announced 2025) enables Step Functions to orchestrate multi-agent pipelines where each agent is a stateful entity with its own session history. The Step Functions event history provides the audit trail; agent-internal state is managed within each agent's session.

**Key properties**: Managed cloud infrastructure, complete CloudWatch execution history, state-level input/output persistence, no deterministic replay, strong operational tooling for debugging.

### 2.7 MCP's JSON-RPC Notification Model

The Model Context Protocol (MCP) uses JSON-RPC 2.0 as its wire format. The March 2025 specification update replaced HTTP+SSE with Streamable HTTP: a single `/messages` endpoint that handles both standard HTTP responses and SSE streams. Servers dynamically decide whether to upgrade a connection to streaming based on the request type.

MCP's notification model provides one-way JSON-RPC frames with no response:

```json
{"jsonrpc": "2.0", "method": "notifications/tools/list_changed", "params": {...}}
```

Lifecycle notifications (`notifications/initialized`) and dynamic updates (`notifications/tools/list_changed`, `notifications/resources/updated`) flow through this channel. For orchestration, this means MCP can serve as an event bus for tool-side events: when a tool's state changes, it notifies the orchestrator without the orchestrator polling.

This is not event sourcing — MCP does not provide a persistent event log or replay capability. But it is the emerging standard for agent-tool and agent-agent communication, and its notification model is structurally compatible with an event-sourced orchestrator that stores MCP notifications as events.

**Key properties**: JSON-RPC 2.0, Streamable HTTP (single endpoint), typed notifications, no persistent event log, standard protocol for agent-tool communication.

### 2.8 EventStoreDB and Marten: Mature Event Store Patterns

EventStoreDB and Marten (PostgreSQL-backed) represent the mature event store ecosystem, and their patterns inform what a production-grade event log requires.

**Core primitives** (from Marten's documentation):
- **Stream identity**: Each aggregate has a distinct event stream, establishing clear transaction boundaries.
- **Append with optimistic concurrency**: `AppendToStream(streamId, expectedVersion, events[])` prevents concurrent writes from creating inconsistent histories.
- **Projections**: Read models built by folding event streams. Marten supports inline projections (synchronous, strong consistency) and async projections (eventual consistency).
- **Snapshots**: Periodic state snapshots reduce replay cost. State = fold(events since snapshot) + snapshot.
- **Event schema versioning**: Upcasting transforms old event schemas to current ones during replay, enabling non-breaking schema evolution.

The CQRS pattern separates the write side (event store commands) from the read side (projections): commands validate against current state, produce events, append to the store; queries read from pre-built projections. This separation is what enables COS's `session_bus.py` to evolve from a coordination log into a true state backbone: commands become event appends, and query surfaces become projections.

A notable 2025 contribution: the "Quick Append" option in Marten/EventStoreDB reduces concurrent write contention by relaxing optimistic concurrency in exchange for higher throughput — exactly the tradeoff COS faces with multiple concurrent agent sessions appending to `events.jsonl` under `fcntl` file lock.

---

## 3. Event-Sourcing Patterns Map

The following table maps the pattern landscape to implementations and their applicability to COS:

| Pattern | Description | Implementations | COS Applicability |
|---|---|---|---|
| **Append-only event log** | Immutable ordered sequence of typed events | COS `events.jsonl`, EventStoreDB, Marten | PRESENT (partial) — missing sequence numbers and schema versioning |
| **Projection / read model** | State derived by folding event stream | LangGraph StateGraph, OpenCode SessionEntryStepper, Marten projections | MISSING — COS reads events directly, no projection layer |
| **Deterministic replay** | Re-executing code against event history to reconstruct state | Temporal, Restate (journal replay) | MISSING — COS has no replay mechanism |
| **Step memoization** | Caching step results, skipping on retry | Inngest steps, LangGraph node checkpoints | MISSING — no per-step persistence in agent harness |
| **Snapshot + delta replay** | Periodic state snapshot reduces replay cost | Temporal history compaction, Marten snapshots, LangGraph checkpoints | MISSING — no snapshot primitives |
| **Optimistic concurrency** | Version-gated appends prevent conflicting writes | EventStoreDB `expectedVersion`, Marten | MISSING — COS uses process-level `fcntl` lock, not stream-level versioning |
| **Stream identity** | Per-aggregate event stream with clear boundaries | EventStoreDB streams, Marten streams, OpenCode Bus vs GlobalBus | PARTIAL — COS has a single global log; no per-agent stream isolation |
| **Sequence-based replay** | Subscriber catches up from arbitrary sequence number | OpenCode `SyncEvent.replay`, EventStoreDB subscriptions | MISSING — COS `read_events` uses tail-limiting, not sequence-from |
| **CQRS separation** | Commands write events; queries read projections | Marten + Wolverine, Axon + Restate, LangGraph | MISSING — COS has unified read/write on the same `events.jsonl` |
| **Typed notifications** | Structured event types with schema validation | MCP JSON-RPC notifications, OpenCode `BusEvent.define`, Temporal Signals | PARTIAL — COS `SESSION_EVENT_TAXONOMY` provides enumeration but no Zod/Pydantic schema per event type |
| **Inter-agent signals** | Events targeted at a specific agent without external bus | Temporal Signals/Queries, OpenCode directed messages | PARTIAL — COS `agent_message_bus.py` implements directed messages but lacks event-log integration |

---

## 4. Deterministic Replay Implications for COS

The orchestration coverage gap analysis (`docs/03-PoCs/research/orchestration-coverage-gap-analysis-2026-05-06.md`) identifies "replay timeline + restore-by-checkpoint" as a critical gap: "Engram captures memory; nothing for 'rewind and re-execute'."

Event sourcing is the enabling primitive for replay. Without it, replay requires:
- A full filesystem snapshot (Devin's VM hypervisor snapshots)
- A CoW block-level snapshot (Replit's manifest pointers)
- A git commit at each decision point (partial coverage via COS's `commit-intent`/`commit-landed` events)

With event sourcing, replay requires only:
1. An immutable, sequenced event log (the events themselves)
2. Pure `apply` functions that fold events into state (projection functions)
3. A way to re-execute agent logic against a past event position (the "replay" operation)

The replay-timeline gap is therefore not independent of the event-sourcing gap. They are the same gap viewed from different angles: replay is the user-facing feature; event sourcing is the architectural substrate that makes it implementable without VM snapshots.

A COS-specific implication: because COS agents are LLM-based, the `exec` function (the LLM call itself) is non-deterministic. This is the same challenge Temporal faces. Temporal's answer: wrap LLM calls as Activities, record their results as events, and during replay inject the stored result without re-calling the LLM. The `apply` function (updating agent state from the LLM output) can still be deterministic even if the `exec` function is not. COS would need the same wrapper pattern: each LLM invocation becomes a durable step whose result is persisted as an event before being consumed.

The `agent-message-sent` and `agent-message-ack` events in COS's taxonomy are already structured this way — they record that a message was sent and acknowledged, which is sufficient to replay the coordination state. What is missing is the same treatment for agent decisions, LLM calls, and tool executions.

---

## 5. COS session_bus Gap Analysis

Comparing `lib/session_bus.py` against the patterns map:

### What COS Has

- Append-only JSONL log at `.cognitive-os/sessions/events.jsonl`
- Process-level `fcntl` exclusive lock for concurrent write safety
- 12-event taxonomy (ADR-183 v1): session-start, branch-acquire, branch-release, coordination-claim, worktree-intake, agent-message-sent, agent-message-ack, agent-spawn, file-write-intent, commit-intent, commit-landed, session-end
- Peer discovery via `peers()`: reads the event log, groups by session_id, filters by PID liveness and timestamp window
- `read_events` with `limit` (tail-based) and `event_type` filter
- Schema version field on every event (`"schema_version": 1`)

### What COS Lacks

1. **Sequence numbers**: Events have `timestamp_epoch` but no monotonic integer sequence. Two events written within the same millisecond are unordered. EventStoreDB and OpenCode's `SyncEvent` use monotonic integers for linearization, gap detection, and replay-from-position.

2. **Per-stream identity**: All agents write to a single global log. OpenCode separates `Bus` (project-scoped) from `GlobalBus` (cross-project). EventStoreDB uses per-aggregate streams. COS cannot isolate the event history of a single agent session without filtering the entire file.

3. **Projection layer**: There is no mechanism to derive read models from the event log. `peers()` re-reads and re-groups on every call. A projection would maintain a live, incrementally-updated view (e.g., a dict of active peer sessions) that costs O(new events) per update rather than O(all events).

4. **Schema per event type**: `SESSION_EVENT_TAXONOMY` is an `frozenset[str]` — it validates event type names but not payload structure. OpenCode's `BusEvent.define` attaches a Zod schema to each event type, ensuring payloads are validated at write time.

5. **Replay-from-sequence**: `read_events(limit=N)` returns the last N events. There is no `read_events(from_sequence=42)` that returns all events from position 42 onward, which is required for subscriber catch-up.

6. **Subscriber model**: COS has no subscription primitive. Consumers must poll `read_events`. OpenCode's `Bus.subscribe` returns a reactive `Stream`; Temporal's `Signal` channel delivers events pushed by the producer.

7. **Event-sourced agent state**: The event log records coordination events, but agent decision state (what the LLM decided, what tools were called, what results were returned) is not recorded as events. It lives in Engram (memory) and in the LLM context window — neither of which supports deterministic replay.

---

## 6. Recommendations: Evolving session_bus into an Event-Sourced Backbone

The following recommendations are ordered by implementation cost and impact. They can be adopted incrementally without breaking backward compatibility.

### Recommendation 1: Add Monotonic Sequence Numbers (Low Cost, High Impact)

Append a `seq` integer to every event. The sequence is a per-project counter stored in a sidecar file (`.cognitive-os/sessions/events.seq`) and incremented atomically under the existing `fcntl` lock.

This single change unlocks:
- Gap detection (subscriber validates `seq == last_seq + 1`)
- Replay from position (`read_events(from_seq=N)`)
- Idempotent event processing (skip `seq <= current`)

Implementation: 10–15 lines in `append_event()`, zero breaking changes to existing consumers (new field, same file).

This is the same mechanism OpenCode's `SyncEvent` uses and the same property EventStoreDB's `expectedVersion` provides. Without sequence numbers, all other event-sourcing patterns are fragile.

### Recommendation 2: Per-Session Event Streams (Medium Cost, High Impact)

Introduce per-session event files: `.cognitive-os/sessions/{session_id}.events.jsonl`. The global `events.jsonl` becomes a fan-out index (event type + session_id + seq only, no payload), while full payloads live in per-session files.

Benefits:
- Session-level stream isolation (replay one agent's history without reading all agents)
- Parallel write paths (each session holds its own lock, eliminating contention)
- Projection cost proportional to session activity, not global event volume

This mirrors OpenCode's Bus (project-scoped) / GlobalBus (cross-project) split. The global log remains for peer discovery; per-session logs become the source of truth for session state.

### Recommendation 3: Projection Layer for Active State (Medium Cost, Medium Impact)

Add a `lib/session_bus_projections.py` module with incremental projectors:

```python
def project_active_peers(events: Iterable[Event]) -> dict[str, PeerSummary]:
    """Fold event stream into live peer map."""
    ...
```

Projectors are called by `append_event` after each write (inline projection, strong consistency) or by a background scanner (async projection, eventual consistency). The current `peers()` function becomes a query against the projection, not a full log scan.

This is the CQRS read-side pattern: commands (append_event) produce events; queries (peers, active_sessions) read projections. The projection state can be persisted as a JSON file alongside the event log (a lightweight "read model database").

### Recommendation 4: Typed Event Schemas with Pydantic (Low Cost, Medium Impact)

Replace `SESSION_EVENT_TAXONOMY: frozenset[str]` with a `dict[str, type[BaseModel]]` mapping event type names to Pydantic models. Each event type defines its payload schema:

```python
class AgentSpawnPayload(BaseModel):
    agent_id: str
    parent_session_id: str
    skill: str
    model: str

EVENT_SCHEMAS: dict[str, type[BaseModel]] = {
    "agent-spawn": AgentSpawnPayload,
    "commit-landed": CommitLandedPayload,
    ...
}
```

`append_event` validates the payload against the schema before writing. This catches malformed events at write time (similar to OpenCode's `BusEvent.define` with Zod), prevents silent data loss from typos in payload field names, and provides a machine-readable contract for projectors.

### Recommendation 5: Durable Agent Steps via event_wrap Decorator (High Cost, High Impact)

For deterministic replay of agent decisions, introduce an `@event_wrap` decorator that records LLM call results as events:

```python
@event_wrap(event_type="llm-invocation-result", session_bus=bus)
async def call_llm(prompt: str) -> str:
    return await llm.invoke(prompt)
```

On first call, the decorator executes `call_llm` and appends a `llm-invocation-result` event with the result. On replay (detected via a replay-mode flag or sequence check), the decorator reads the stored result from the event log and returns it without re-invoking the LLM.

This is the same pattern Temporal uses for Activities and Inngest uses for `step.run`. It is the foundational primitive for deterministic replay without VM snapshots, and it directly closes the "replay determinism" gap identified in the coverage analysis.

This recommendation requires the most design work (replay mode flag, LLM call interception, event-log lookup) but delivers the highest strategic value: it transforms COS from "event log for coordination" to "event-sourced execution engine for agent decisions."

---

## 7. Implementation Priority Matrix

| Recommendation | Cost | Impact | Risk | Priority |
|---|---|---|---|---|
| Monotonic sequence numbers | Low | High | Low | **Immediate** |
| Typed event schemas (Pydantic) | Low | Medium | Low | **Immediate** |
| Per-session event streams | Medium | High | Low | **Next sprint** |
| Projection layer | Medium | Medium | Low | **Next sprint** |
| Durable agent steps (@event_wrap) | High | High | Medium | **Planned — links to replay-timeline gap** |

---

## 8. Connection to the Replay-Timeline Gap

The replay-timeline gap (identified in the coverage analysis as a critical competitive gap against Devin's "scrub timeline" feature) is architecturally downstream of the event-sourcing gap. The path is:

```
Monotonic sequences (Rec 1)
        ↓
Per-session streams (Rec 2)
        ↓
Durable agent steps (Rec 5)  ←  "every decision is an event"
        ↓
Replay-from-sequence         ←  "fold events to any historical point"
        ↓
Replay timeline UI / CLI     ←  "cos replay --session abc --to-seq 42"
```

Recommendations 1 and 2 are prerequisites. Recommendation 5 is the key enabler. The replay timeline UI is a thin layer on top — once the event log contains all decisions and their results in sequence, "scrubbing" is simply selecting a sequence position and re-projecting state.

---

## Sources

1. [Temporal: Durable Execution Meets AI](https://temporal.io/blog/durable-execution-meets-ai-why-temporal-is-the-perfect-foundation-for-ai)
2. [Temporal: Beyond State Machines for Distributed Applications](https://temporal.io/blog/temporal-replaces-state-machines-for-distributed-applications)
3. [Temporal: Orchestrating Ambient Agents](https://temporal.io/blog/orchestrating-ambient-agents-with-temporal)
4. [OpenCode Event Bus Architecture — DeepWiki](https://deepwiki.com/sst/opencode/2.8-storage-and-migration-system)
5. [OpenCode Session Management — DeepWiki](https://deepwiki.com/sst/opencode/2.1-session-management)
6. [Inside OpenCode: Building an AI Coding Agent — Medium](https://medium.com/@gaharwar.milind/inside-opencode-how-to-build-an-ai-coding-agent-that-actually-works-28c614494f4f)
7. [LangGraph Multi-Agent Orchestration 2025 — Latenode Blog](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025)
8. [LangGraph Overview — LangChain Docs](https://docs.langchain.com/oss/python/langgraph/overview)
9. [Inngest: How Functions Are Executed (Durable Execution)](https://www.inngest.com/docs/learn/how-functions-are-executed)
10. [Inngest Blog: Your Agent Needs a Harness, Not a Framework](https://www.inngest.com/blog/your-agent-needs-a-harness-not-a-framework)
11. [Restate: Build Innately Resilient Distributed Apps](https://www.restate.dev/)
12. [Kai Waehner: Rise of Durable Execution Engines (Temporal, Restate) with Kafka](https://www.kai-waehner.de/blog/2025/06/05/the-rise-of-the-durable-execution-engine-temporal-restate-in-an-event-driven-architecture-apache-kafka/)
13. [Zylos Research: Durable Execution Patterns for AI Agents](https://zylos.ai/research/2026-02-17-durable-execution-ai-agents)
14. [Marten: Understanding Event Sourcing](https://martendb.io/events/learning.html)
15. [Marten: Event Store Documentation](https://martendb.io/events/)
16. [Eulerfx GitHub Gist: State Machines and Event Sourcing](https://gist.github.com/eulerfx/4ac420a14422ac960222)
17. [Christian Posta: MCP HTTP+SSE Architecture Change](https://blog.christianposta.com/ai/understanding-mcp-recent-change-around-http-sse/)
18. [AWS: Temporal + Amazon Bedrock AgentCore](https://aws.amazon.com/blogs/apn/how-temporal-uses-amazon-bedrock-agentcore-to-create-robust-ai-systems/)
19. [Axon + Restate: CQRS and Event Sourcing with Durable Execution](https://www.axoniq.io/events/cqrs-and-event-sourcing-with-durable-execution-using-axon-and-restate-webinar)
20. [MCP Connector Documentation — Anthropic](https://docs.anthropic.com/en/docs/agents-and-tools/mcp-connector)
21. [Building Agent Teams in OpenCode — DEV Community](https://dev.to/uenyioha/porting-claude-codes-agent-teams-to-opencode-4hol)
