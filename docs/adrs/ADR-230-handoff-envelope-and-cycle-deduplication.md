# ADR-230 — Agent Handoff Envelope + Call-Chain Deduplication

<!-- SCOPE: OS -->

**Status**: Accepted — Slices A–E implemented (2026-05-07)
**Date**: 2026-05-06
**Related**: ADR-203 (subagent capability contract), ADR-211 (service mode readiness), ADR-225 (branch-per-task — reserved); depends on ADR-226 (event-sourced session bus); pairs with ADR-233 (cross-session agent teams)
**Source**: [`docs/research/orchestration-gaps/agent-to-agent-handoff.md`](../research/orchestration-gaps/agent-to-agent-handoff.md). Production failure rate of 41–87% on state-of-the-art open-source multi-agent systems (MAST 2025 paper). The #1 production failure mode is the infinite handoff loop: agent A delegates to B who delegates to C who re-delegates back to A. **Zero frameworks prevent this.** Cognitive OS today has no handoff protocol at all — every cross-agent call routes through the orchestrator — but ADR-211 service mode and ADR-233 cross-session teams both anticipate one. This ADR ships the protocol.

---

## Context

Three failure modes the field has not solved:

1. **Infinite handoff loops.** Without call-chain tracking, A→B→C→A is invisible to every participant. Each hop loses context (because no envelope carries the chain), and the operator only notices when the bill arrives or the agent finally exhausts its retry budget.
2. **Context-passing without consensus.** Three patterns exist (full history, summarization, reference-only), each with documented failure modes. The right move is to make the choice *explicit* per handoff — a `context_mode` field on the envelope — rather than baking one strategy into the orchestrator.
3. **Permission inheritance silently expands blast radius.** OpenAI Swarm and Anthropic Agent Teams both default to flat inheritance — a sub-agent has the orchestrator's blast radius. A compromised or misconfigured sub-agent can therefore do everything the caller could. The right model (per ElevenLabs and the prior-art research) is *intersection*: the delegated agent gets `caller_grants ∩ receiver_manifest_declares`.

Cognitive OS has no current protocol for any of this. The orchestrator hub-and-spoke model worked for in-session subagents but is not adequate for the cross-session agent-team flows ADR-233 introduces. ADR-230 fills that vacuum **before** ADR-233 ships agent-team coordination, so agent-teams have a typed contract from day one.

The protocol design borrows from two reference patterns (per C1 — pattern-only adoption):

- **Google A2A `referenceTaskIds`** (Apache-2.0): the reference-only context-passing mode. Agents pass an opaque task ID and the receiver fetches context as needed.
- **LangGraph `Command`** (MIT): the typed envelope shape with `goto` semantics. We adopt the shape; we do not link the library.

Both are open-source, both production-validated, both have permissive licenses. ADR-230 implements the union of their best ideas under our license.

## Decision

Ship `lib/handoff_envelope.py` + `lib/handoff_dispatcher.py` as the canonical handoff protocol. Three primitives:

1. **`HandoffEnvelope` typed struct** — every cross-agent call (subagent or cross-session) MUST construct one. Carries identity, context mode, granted tools, depth, and the call chain.
2. **Call-chain deduplication** — before any handoff, the dispatcher checks if `to_agent` is already in the current `call_chain`. If yes, raise `HandoffCycleDetected` and terminate cleanly with diagnostic. **<1 day of code, highest-ROI safety primitive in the orchestration space.**
3. **Permission intersection** — granted tools are the intersection of (a) what the caller can grant and (b) what the receiver's manifest declares it accepts. Implemented via `lib/agent_capability_index.py` (already exists from ADR-203) plus a dispatcher-side intersection.

## `HandoffEnvelope` shape

```python
# lib/handoff_envelope.py
@dataclass(frozen=True)
class HandoffEnvelope:
    schema_version: str         # "handoff-envelope/v1"
    handoff_id: str             # uuid4, unique per handoff event
    parent_event_seq: int       # ADR-226 event seq this handoff is causally after
    from_agent: str             # caller identity (orchestrator | subagent:<id> | session:<id>)
    to_agent: str               # receiver identity (same shape)
    intent: str                 # "delegate" | "handoff" | "query" — see below
    context_mode: str           # "full" | "summary" | "reference" | "none"
    context_payload: dict       # mode-specific shape
    granted_tools: list[str]    # intersection result; empty list = read-only
    granted_blast_radius: int   # max files agent may modify
    depth: int                  # 0 for orchestrator-originated; +1 per hop
    call_chain: list[str]       # [from_agent identities back to root]
    deadline_ts: str | None     # ISO-8601, optional wallclock cap
    return_control: bool        # True = handoff (no return); False = delegate (must return)
```

### Intent semantics

- **`delegate`**: caller awaits receiver's result. Receiver must `return` an envelope-shaped reply or fail. Used for "do this subtask and report back."
- **`handoff`**: caller transfers control. Receiver does not return; the next operator-visible state is the receiver's choice. Used for "this isn't my problem anymore."
- **`query`**: read-only information request. Receiver returns a result; permission set is forced to read-only regardless of manifest.

### Context modes

- **`full`**: entire conversation history, base64-or-inline. Quadratic cost; only for short chains.
- **`summary`**: compressed by orchestrator; carries `compression_method` + `summary_seq_range`. Lossy; default for chains > 3 hops.
- **`reference`**: opaque IDs back to ADR-226 event seqs and shadow-git tree SHAs (ADR-227). Receiver fetches as needed. Most efficient; default for cross-session.
- **`none`**: only `intent` and minimal payload. For pure-function delegations (e.g., "translate this string").

## Call-chain deduplication

```python
# lib/handoff_dispatcher.py (excerpt)
def dispatch_handoff(envelope: HandoffEnvelope) -> HandoffEnvelope | HandoffResult:
    # Cycle check — the highest-ROI safety primitive in the orchestration space
    if envelope.to_agent in envelope.call_chain:
        raise HandoffCycleDetected(
            cycle=envelope.call_chain + [envelope.to_agent],
            envelope=envelope,
        )

    # Depth check — defense in depth against pathological chains even without a literal cycle
    if envelope.depth > MAX_HANDOFF_DEPTH:
        raise HandoffDepthExceeded(envelope=envelope)

    # Permission intersection
    receiver_accepts = capability_index.lookup(envelope.to_agent).accepts
    granted_tools = list(set(envelope.granted_tools) & set(receiver_accepts))
    if granted_tools != envelope.granted_tools:
        envelope = replace(envelope, granted_tools=granted_tools)
        emit_event("handoff.permission.scoped_down", envelope.handoff_id, ...)

    # Blast radius gate — exits 2 to operator if exceeded
    if envelope.granted_blast_radius > BLAST_RADIUS_OPERATOR_THRESHOLD:
        if not operator_approve_handoff(envelope):
            raise HandoffBlockedByOperator(envelope=envelope)

    # Deliver
    return _deliver(envelope)
```

`MAX_HANDOFF_DEPTH = 7` by default (configurable in manifest). The MAST paper documented production cycles at depth 12+; capping at 7 catches pathology without blocking legitimate hierarchical workflows.

## Manifest declaration

```yaml
# manifests/handoff-protocol.yaml
schema_version: handoff-envelope/v1
status: active
owner: platform-orchestration

dispatcher:
  max_handoff_depth: 7
  default_context_mode_by_depth:
    "0..2": "full"
    "3..5": "summary"
    "6+": "reference"
  blast_radius_operator_threshold: 50      # files; gate triggers above
  cycle_detection: required

intent_types:
  delegate:
    awaits_return: true
    default_timeout_seconds: 300
  handoff:
    awaits_return: false
    transfers_control: true
  query:
    awaits_return: true
    forces_read_only: true

context_modes:
  full:
    payload_schema: "conversation_history_v1"
    max_chain_depth: 3                     # advisory; not enforced
  summary:
    payload_schema: "summary_payload_v1"
    requires_field: ["compression_method", "summary_seq_range"]
  reference:
    payload_schema: "reference_payload_v1"
    requires_field: ["event_seq_range", "file_tree_sha", "session_id"]
  none:
    payload_schema: "minimal_payload_v1"

permission_intersection:
  source_a: "caller.granted_tools"
  source_b: "receiver.manifest.accepts (lib/agent_capability_index.py)"
  result: "set_intersection"
  scoped_down_event: "handoff.permission.scoped_down"

hooks:
  pre_handoff: "HandoffRequested"          # fires before dispatch; can block
  post_handoff: "HandoffCompleted"
  on_cycle: "HandoffCycleDetected"
  on_depth_exceeded: "HandoffDepthExceeded"
  on_blast_radius_block: "HandoffBlockedByOperator"

emitted_events:                            # ADR-226 event types
  - handoff.requested
  - handoff.dispatched
  - handoff.permission.scoped_down
  - handoff.completed
  - handoff.cycle_detected
  - handoff.depth_exceeded
  - handoff.operator_blocked
```

## Hard rules

- **Every cross-agent call constructs an envelope.** No raw `dispatch_to_agent(prompt)` calls. CI test asserts.
- **Cycle detection is mandatory and runs before any other check.** If a cycle is detected, no event other than `cycle_detected` fires; no permission scope-down event fires; the handoff is rejected at the door.
- **Permission intersection is enforced server-side** (in the dispatcher), not client-side. A caller asking to grant tools the receiver doesn't accept does not produce an error — it produces a scoped-down envelope and an event. The caller can inspect the result.
- **Operator-in-loop above blast-radius threshold.** Any handoff with `granted_blast_radius > BLAST_RADIUS_OPERATOR_THRESHOLD` triggers `HandoffRequested` hook with exit-code-2 capability. Operator approves or denies.
- **Schema-versioned.** Every envelope carries `schema_version: handoff-envelope/v1`. Receivers MUST check.
- **Idempotency on `handoff_id`.** Re-delivering the same envelope (e.g., on retry) MUST NOT produce duplicate side effects. Receiver tracks `handoff_id` for ADR-228 idempotency-window TTL.
- **No external runtime dependencies.** Honors C2.

## Test tier matrix (per C3)

T1 ✅ unit — envelope construction, cycle detection, permission intersection
T2 ✅ integration — dispatch round-trip; chain depth 0..7 OK, 8+ raises
T3 ✅ behavior — manifest validation; intent semantics (delegate vs handoff vs query)
T4 ✅ smoke — fresh session, agent A delegates to B, B delegates to A → cycle detected
T5 ✅ adversarial — concurrent same-handoff_id (idempotency), permission-grant-of-undeclared-tool, malformed envelope
T6 ⬜ performance — covered indirectly; not a hot-path
T7 ✅ chaos — kill mid-dispatch, kill mid-receiver-execution, lost return envelope
T8 ✅ cross-harness — works on Claude Code subagents, Codex agents, OpenCode subagents
T9 ⬜ adoption-truth — pattern-only adoption (A2A + LangGraph Command); no external lib pinned
T10 ⬜ audit invariants — N/A (no git/WT mutation)

## Consequences

### Positive

- **Closes the #1 production multi-agent failure mode** (cycles) at <1 day of code. The single highest-ROI item in the entire orchestration plan per the research.
- **Typed envelope replaces ad-hoc string passing** across subagent and cross-session calls. ADR-211 service mode and ADR-233 agent teams both consume the same shape.
- **Permission intersection narrows blast radius** automatically. Operators don't have to remember to scope tools per delegation.
- **Operator-in-loop above threshold** preserves ADR-055b governance posture (destructive ops require explicit consent).
- **Future-compatible with A2A** if cross-vendor interop ever becomes a requirement. Envelope shape is a strict subset of A2A message-parts.
- **Composable with ADR-228 retry**: a failed handoff classifies via the retry contract; idempotency keys ride on `handoff_id`.

### Negative / trade-offs

- **One more typed struct in the dispatch path.** Mitigation: it's a frozen dataclass; construction is sub-millisecond.
- **Operators may find the four context modes confusing.** Mitigation: manifest declares automatic defaults by depth; explicit override is for advanced users only.
- **Permission intersection can scope down a delegation the caller actually intended.** Mitigation: scoped-down emits an event the caller can inspect; the caller may then decline to proceed if the intersection is too narrow.
- **The protocol is more ceremony than the field's status quo.** Mitigation: the field's status quo is producing 41-87% failure rates. Ceremony is the price of correctness here.

## Alternatives rejected

- **Hub-and-spoke through orchestrator (status quo).** Doesn't scale to ADR-233 cross-session teams; orchestrator becomes a bottleneck and an SPoF.
- **Adopt LangGraph Command directly.** MIT (allowlist) but pulls in LangGraph's runtime model. Pattern adoption is sufficient.
- **Adopt Google A2A protocol directly.** Apache 2.0 OK; over-engineered for our scope (designed for cross-org task delegation). Adopt the `referenceTaskIds` shape; skip the rest.
- **Per-handoff JSON over stdio (loose typing).** Considered; rejected because typing is the entire point — a frozen dataclass catches misuse at construction, not at delivery.
- **No depth cap, only cycle cap.** Considered; rejected because pathological chains can be acyclic but unbounded.
- **Make permission intersection opt-in.** Rejected; opt-in is opt-in-blast-radius-expansion.
- **Encode handoff intent as a flag rather than enum.** Rejected; three intents have different semantics that benefit from explicit dispatch.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_handoff_envelope.py tests/unit/test_handoff_dispatcher.py tests/integration/test_handoff_round_trip.py tests/audit/test_no_raw_dispatch_to_agent.py tests/behavior/test_handoff_manifest.py tests/chaos/test_handoff_kill_mid_dispatch.py -q

# Smoke (T4)
python3 -m pytest tests/unit/test_handoff_envelope.py tests/unit/test_handoff_dispatcher.py tests/behavior/test_handoff_dispatcher_flow.py tests/behavior/test_cos_team_cli.py -q
bash tests/smoke/test_handoff_cycle_detection.sh
```

The tests must prove:

- `HandoffEnvelope` construction with required fields succeeds; missing fields raise.
- `dispatch_handoff` with `to_agent in call_chain` raises `HandoffCycleDetected` *before* any event other than the cycle event fires.
- `depth > MAX_HANDOFF_DEPTH` raises `HandoffDepthExceeded`.
- Permission intersection: `granted_tools=[a, b, c]` with receiver accepts `[b, d]` results in `granted_tools=[b]` and emits `handoff.permission.scoped_down`.
- `intent="query"` forces empty `granted_tools` regardless of caller intent.
- `intent="handoff"` does not await return; control transfers; orchestrator state reflects new owner.
- Idempotent re-delivery of same `handoff_id` does not duplicate side effects.
- `granted_blast_radius > threshold` triggers `HandoffRequested` hook; if hook exits 2, dispatch raises `HandoffBlockedByOperator`.
- Round-trip on fixture: A→B→A produces cycle detection event.
- Round-trip on fixture chain depth 5: each hop carries correct call_chain; final receiver sees full chain.
- CI audit: no `dispatch_to_agent(prompt)` raw calls; all routed through envelope.

## Implementation slices

1. **Slice A — `lib/handoff_envelope.py`** (~50 LOC). The frozen dataclass + construction validators. Tests T1.
2. **Slice B — `lib/handoff_dispatcher.py` cycle + depth detection** (~40 LOC). The highest-ROI <1-day item. Tests T1+T2+T4.
3. **Slice C — Permission intersection** (~30 LOC). Wire `lib/agent_capability_index.py` (existing). Emit scoped-down event. Tests T1+T5.
4. **Slice D — Hook integration** (~30 LOC). Register `HandoffRequested`, `HandoffCompleted`, `HandoffCycleDetected`, etc. as ADR-226 event types. Tests T2+T3.
5. **Slice E — Manifest + audit test** (~rule-only + ~30 LOC test). `manifests/handoff-protocol.yaml` + CI test asserting no raw `dispatch_to_agent` calls in `hooks/`, `scripts/`, `lib/`. Tests T9 audit.
6. **Slice F — Operator runbook** at `docs/runbooks/handoff-troubleshooting.md`. Three flows: cycle-detected, blast-radius-block, depth-exceeded.

Total: ~180 LOC. Slice B alone (cycle dedup) is the <1-day high-ROI MVP.

## Implementation status (2026-05-07)

Slices A–E are implemented as the first executable handoff contract:

- `packages/agent-lifecycle/lib/handoff_envelope.py` (+ `lib/handoff_envelope.py` symlink) defines the frozen `HandoffEnvelope` schema, validators, JSON round-trip, and next-hop lineage helper.
- `packages/agent-lifecycle/lib/handoff_dispatcher.py` (+ `lib/handoff_dispatcher.py` symlink) enforces cycle detection before any secondary side effect, max-depth checks, query read-only semantics, receiver tool intersection, blast-radius operator blocking, event emission through ADR-226, and idempotent handoff replay.
- `manifests/handoff-protocol.yaml` declares the active policy, emitted events, hooks, intent semantics, context modes, and permission-intersection invariant.
- Tests cover unit, behavior, smoke, and audit lanes: `tests/unit/test_handoff_envelope.py`, `tests/unit/test_handoff_dispatcher.py`, `tests/behavior/test_handoff_dispatcher_flow.py`, `tests/audit/test_handoff_manifest.py`, and `tests/smoke/test_handoff_cycle_detection.sh`.

Slice F transport is implemented for file-IPC delivery: `cos team handoff send` dispatches the ADR-230 envelope through `HandoffDispatcher` and delivers the scoped envelope as an ADR-233 inbox message. A cross-harness contract test proves Codex-style and Claude-style session ids share the same transport. This is real cross-session file-IPC transport, not receiver execution.

Slice G receiver execution is implemented as an explicit operator-controlled command: `cos team handoff receive --exec-command-template ...` reads ADR-233 inbox handoffs, validates envelopes, writes idempotency receipts, and optionally executes a bounded shell template.

Slice H external receiver hooks are implemented via `cos team handoff receive --hook-command ...`: the envelope is passed on stdin, `COS_HANDOFF_*` environment variables are set, timeout is bounded, and strict-mode failures/timeouts write receipts before returning exit 2.

Process-kill chaos is implemented in `tests/chaos/test_handoff_receiver_kill_mid_dispatch.py`: timeout and SIGKILL receiver failures both persist receipts before returning failure, and a second receive skips the failed handoff idempotently. The current slices intentionally do not spawn agents or mutate worktrees.

## Open questions

- **Should `query` intent be denied entirely if the receiver is not declared idempotent?** Initial answer: no — query is read-only by definition; idempotency is for state-mutating tools. Document explicitly.
- **How does `context_mode=summary` choose its compression?** Initial answer: orchestrator picks; eventually a per-receiver hint can override. Defer the override surface to a later slice.
- **Cross-vendor envelope interop with A2A.** Defer; the envelope is a strict subset, so A2A interop is a translation layer when needed.
- **Should `granted_blast_radius` be a count or a path-pattern set?** Initial answer: count (matches existing `blast_radius` hook semantics). Path-pattern set is a Phase-2 refinement if false positives bite.
- **Handoff persistence across crashes.** ADR-226 sequences cover the event log; the dispatcher itself is stateless. A crash mid-dispatch leaves the envelope in the event log for recovery; the handoff is re-attempted by the recovering session via the idempotency-key mechanism.
