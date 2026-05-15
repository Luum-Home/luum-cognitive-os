---
adr: 183
title: Cross-Session Event Log — Append-Only Visibility for Peer Orchestrators
status: accepted
implementation_status: implemented
date: 2026-05-05
supersedes: []
superseded_by: null
extends: []
implementation_files:
- lib/session_bus.py
- scripts/session_event_bus.py
- lib/session_coordination.py
- lib/agent_message_bus.py
- scripts/cos-session-coordination
- scripts/cos-agent-message
- hooks/cross-session-event-emit.sh
- hooks/cross-session-peer-context.sh
- tests/unit/test_cross_session_events.py
tier: maintainer
tags:
- concurrency
- observability
- governance
- postmortem-2026-05-05
---
# ADR-183: Cross-Session Event Log — Append-Only Visibility for Peer Orchestrators

## Status

**Accepted.** Implemented as an extension of the existing `lib/session_bus.py` plus emit/context hooks. Companion to ADR-182. ADR-182 prevents *conflicts*; ADR-183
provides *awareness* — even when sessions do not contend on the same
branch, the orchestrator should know that peer sessions exist and what
they are doing.

## Context

The post-mortem revealed that tonight's session orchestrator-LLM had no
mechanism to detect that a second orchestrator was working on related
material (Paperclip rejection / cleanup). Each session operated as if
sovereign, leading to duplicated work plus contradictory disposition
policies (annotate-and-keep vs delete-and-tombstone) on the same
subject.

COS already has a minimal shared append-only bus:

- `lib/session_bus.py`
- `scripts/session_event_bus.py`
- `.cognitive-os/sessions/events.jsonl`

The gap is not absence of any bus. The gap is that the existing bus is too
generic and too lightly wired: it does not yet emit the full cross-session
taxonomy, summarize peer activity at `UserPromptSubmit`, or connect cleanly to
the claim ledger and directed message bus.

## Decision

Extend the existing **cross-session append-only event log** with a fixed event
schema, plus two hooks: one that emits events from each session, one that reads
recent events and injects peer awareness into the orchestrator's context.

### Event log

File: `.cognitive-os/sessions/events.jsonl`

Append-only, never rewritten. One JSON object per line. ADR-183 standardizes
the payload shape on top of the current `session_bus.append_event()` format:

```json
{
  "schema_version": 1,
  "timestamp_epoch": 1778012502.123,
  "event_type": "branch-acquire",
  "session_id": "1778012502-40406-0062edf8",
  "pid": 40406,
  "project_dir": "/Users/.../luum-agent-os",
  "payload": {
    "branch": "session/41961ce2-paperclip-rejection-multi-surface",
    "worktree": "/Users/.../luum-agent-os",
    "topic_keywords": ["paperclip", "rejection"]
  }
}
```

### Event taxonomy

Required emitters:

- `session-start` — session begins (SessionStart hook)
- `branch-acquire` — branch lock acquired (ADR-182 hook emits this)
- `branch-release` — branch lock released
- `coordination-claim` — session claims an ADR number, path, policy, skill,
  primitive, or task through the coordination ledger
- `worktree-intake` — session records read-only/import/ignore intake for a
  sibling worktree
- `agent-message-sent` — directed message sent through the agent message bus
- `agent-message-ack` — directed message acknowledged
- `agent-spawn` — sub-agent launched (PreToolUse Agent)
- `file-write-intent` — about to write to a path (PreToolUse Write/Edit;
  emit `path` and short content hash)
- `commit-intent` — about to commit (PreToolUse Bash matcher commit)
- `commit-landed` — commit successful (PostToolUse same matcher)
- `session-end` — session terminates (Stop hook)

This is an **open taxonomy with a pinned v1 floor**. New event types may be
added as coordination needs grow, but the v1 set above must not regress. The
runtime constant `SESSION_EVENT_TAXONOMY` in `lib/session_bus.py` and the
contract test `tests/contracts/test_cross_session_event_taxonomy.py` pin this
floor while still allowing future producers to append new event types.

Current wiring covers:

- `hooks/cross-session-event-emit.sh` for `session-start`,
  `file-write-intent`, `agent-spawn`, `commit-intent`, `commit-landed`, and
  `session-end`;
- `lib/branch_lock.py` for `branch-acquire` and `branch-release`;
- `lib/agent_message_bus.py` for `agent-message-sent` and
  `agent-message-ack`;
- existing coordination/intake producers for `coordination-claim` and
  `worktree-intake`.

### Peer context injection

Hook `hooks/cross-session-peer-context.sh` runs at UserPromptSubmit:

1. Reads the last 200 events from `.cognitive-os/sessions/events.jsonl`.
2. Filters events from sessions other than the current one within the
   last 30 minutes that are still alive.
3. For each peer: summarize active branch, recent file-write intents,
   active topics inferred from agent spawns.
4. Emit `additionalContext`:

```
Peer orchestrator sessions detected:
- session 1778032365-... on branch session/50c35ce9-remove-paperclip-...
  recently writing: docs/02-Decisions/adrs/ADR-043-*, lib/paperclip_client.py
  topic: paperclip purge
Coordinate before issuing conflicting changes.
```

The orchestrator-LLM thus sees in real-time that a peer is working on
related material and can either back off, coordinate via Engram, or
escalate to the operator.

### Event log rotation

Rotate when file exceeds 50 MB or weekly. Old logs go to
`.cognitive-os/sessions/events-archive/<YYYY-MM>.jsonl.gz`. The
peer-context hook only reads the live log.

## Acceptance Criteria

1. `lib/session_bus.py` remains the canonical append-only writer and is
   extended, or wrapped by a thin peer-summary helper, to expose:
   - `append_event(event_type: str, payload: dict | None = None) -> dict`
   - `read_events(limit: int | None = None, event_type: str | None = None) -> list[dict]`
   - `peers(within_seconds: int = 1800, alive_only: bool = True) -> list[PeerSummary]`
   - `PeerSummary(session_id, branch, last_seen, topic_keywords, recent_writes)`
2. `hooks/cross-session-event-emit.sh` is invoked at: SessionStart,
   PreToolUse Agent/Write/Edit/Bash matcher commit, PostToolUse same,
   Stop. Each invocation calls the appropriate `emit()`.
3. `hooks/cross-session-peer-context.sh` runs at UserPromptSubmit;
   latency budget < 100 ms; emits non-empty `additionalContext` only
   when peers exist.
4. Event log is git-ignored.
5. Tests: synthetic JSONL with 2 sessions; peer-context hook detects
   the peer in the orchestrator's session and includes its summary in
   `additionalContext`.
6. Killswitch: `DISABLE_HOOK_CROSS_SESSION_EVENT_EMIT=1` and
   `DISABLE_HOOK_CROSS_SESSION_PEER_CONTEXT=1` env vars.

## Border Cases

- **Single-session usage**: peer-context hook emits empty
  `additionalContext`. No noise.
- **Many sessions** (operator running 5+ tabs): peer-context truncates
  to 3 most-relevant peers (most recently active and most topic-
  overlapping with current prompt).
- **Stale events from dead sessions**: filtered by `alive_only=True`
  via PID check.
- **Operator suppresses peer awareness intentionally**: env var
  override per session.
- **High-frequency event emission**: rate-limit per session to 1 event
  per 100 ms to prevent log overload from a runaway agent.

## Consequences

### Positive

- Orchestrator-LLM gains peer awareness without operator manual
  inspection.
- Tonight's incident pattern (two sessions silently writing
  contradictory ADR content) becomes detectable: the second session's
  `file-write-intent` for `ADR-171-tombstone.md` would surface in the
  first session's UserPromptSubmit context, prompting coordination.
- Provides a debuggable audit trail of inter-session activity.

### Negative

- Adds disk I/O on every relevant tool call.
- Privacy: file paths and short topic keywords leak between sessions
  on the same machine. Mitigation: opt-out env var; the data is local
  to the operator's workstation.
- Requires a small new dependency: tail-style read of a JSONL with PID
  checks.

### Neutral

- This is *advisory*, not enforcing. ADR-182 enforces; ADR-183
  informs.

## Operational Guide

### What changes for the operator

Before this ADR, each session operated as if sovereign: no session could
see that a peer was working on related material without manually checking
`active-sessions.json`. The 2026-05-05 incident showed two sessions
writing contradictory disposition policies on the same subject with zero
mutual awareness.

After this ADR:

- Every significant tool call (session-start, branch-acquire, file
  write intent, agent-spawn, commit, session-end) emits a structured
  event to `.cognitive-os/sessions/events.jsonl`.
- At every `UserPromptSubmit`, the orchestrator receives a peer-context
  summary injected by `hooks/cross-session-peer-context.sh` if any live
  peer sessions exist.
- The peer-context summary names the peer's active branch, recent
  write targets, and inferred topics so the orchestrator can coordinate
  before issuing conflicting changes.
- The log is advisory, not enforcing. ADR-182 enforces (blocks
  conflicting commits); ADR-183 informs (surfaces peer activity in
  context).

To suppress peer awareness for a session: set
`DISABLE_HOOK_CROSS_SESSION_PEER_CONTEXT=1`.

### What this answers (and what it doesn't)

**Answers:**
- "Is anyone else working on related material right now?" — Peer-context
  injection shows peer sessions active in the last 30 minutes with their
  branch, recent writes, and topic keywords.
- "What happened in other sessions recently?" — Read
  `.cognitive-os/sessions/events.jsonl` directly; filter by
  `session_id` to isolate per-session activity.
- "When did a peer acquire the branch lock?" — Look for
  `event_type: branch-acquire` in the log.

**Does not answer:**
- Whether a peer's changes are semantically compatible with the current
  session's work. The log surfaces activity; compatibility judgment
  remains with the operator or orchestrator.
- Cross-machine peer activity. Events are local to the machine.
  ADR-136 / ADR-141 handle cross-machine memory.

### Daily operational pattern

1. Sessions emit events automatically via registered hooks; no manual
   action required.
2. At each `UserPromptSubmit`, the orchestrator sees injected peer
   context (if peers exist). The orchestrator decides whether to
   coordinate, back off, or escalate.
3. To inspect recent cross-session activity manually:
   ```bash
   python3 -c "
   import json, time
   with open('.cognitive-os/sessions/events.jsonl') as f:
       for line in f:
           e = json.loads(line)
           if time.time() - e['timestamp_epoch'] < 1800:
               print(e['event_type'], e['session_id'][:12], e.get('payload',{}))
   "
   ```
4. Log rotation happens at 50 MB or weekly; old logs go to
   `.cognitive-os/sessions/events-archive/<YYYY-MM>.jsonl.gz`.

### When sources disagree

If the peer-context hook claims a peer is active but the operator knows
that session has ended:

1. Check whether the peer PID is alive:
   `ps aux | grep <pid>` (PID is in `session-start` events).
2. If the PID is dead, the peer filter (`alive_only=True`) should have
   excluded it. If the hook still shows the peer, it may be using a
   cached read; re-running the next prompt will refresh the filter.
3. The event log itself is always current (append-only). The peer-context
   hook reads only the last 200 events; older events are not used for
   peer detection.

## Alternatives rejected

- **Engram pub/sub**: heavy, requires the Engram daemon to be running,
  fails open if Engram is down. Rejected as primary; Engram remains the
  durable memory layer.
- **Valkey agent-bus** (existing infra, mostly OFF): would work but
  requires the agent-bus to be on by default, which violates the
  current "agent-bus is opt-in" doctrine.
- **Filesystem inotify**: not portable across all platforms COS targets.

## Falsifiable Claim

ADR-183 is correct if, in a 90-day audit window, peer-context
injection causes the orchestrator-LLM to (a) detect peer activity in
≥ 95 % of multi-session events, and (b) measurably reduce duplicate-
or-conflicting commits across sessions. Detection lag must be < 60
seconds in the worst case.

If after 90 days the conflict rate has not decreased OR detection lag
exceeds 60 seconds at 99th percentile, the design is broken and ADR-183
must be revisited.

## Cross-References

- `docs/06-Daily/reports/postmortem-cross-session-collision-2026-05-05.md` —
  origin.
- ADR-182 — branch ownership lock (companion: prevents conflict;
  ADR-183 surfaces it).
- ADR-088 commit_provenance — same metadata channel
  (`X-COS-Origin/Session`) but post-hoc.
- ADR-058 observability migration to Phoenix — Phoenix consumes traces;
  ADR-183 events could be mirrored to Phoenix as a future enhancement.
- ADR-184 manager-of-managers daemon — when present, daemon consumes
  this event log to make global decisions.
- `lib/session_bus.py` — current event-log implementation extended by this ADR.
- `docs/04-Concepts/architecture/cross-session-coordination-ledger.md` — claim and intake
  producer for coordination events.
- `docs/04-Concepts/architecture/agent-message-bus.md` — directed message producer for
  audit/implementation events.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

