# ADR-233 — Cross-Session Agent-Team File IPC

<!-- SCOPE: OS -->

**Status**: Accepted — Slice A implemented (2026-05-07)  
**Date**: 2026-05-07  
**Related**: ADR-211 (service readiness), ADR-226 (event-sourced session bus), ADR-230 (handoff envelope), ADR-231 (MCP server surface), ADR-235 (detached agent daemon)  
**Source**: [`docs/research/orchestration-gaps/cross-session-agent-teams.md`](../research/orchestration-gaps/cross-session-agent-teams.md)

---

## Context

Subagents live inside one parent session. Agent teams are independent sessions that coordinate across process boundaries. COS already had `TeammateIdle`, `TaskCreated`, and `TaskCompleted` hooks, but lacked a canonical file-IPC contract for team membership, tasks, inbox messages, and events.

The prior-art research shows same-machine file IPC is the right first tier: append-only JSONL, advisory locks, and no daemon or network dependency.

## Decision

Build the first cross-session team substrate as `lib/agent_team.py` backed by `.cognitive-os/teams/<team-name>/`:

- `members.jsonl` — append-only session registry.
- `tasks.jsonl` — event-sourced task manifest with locked claims.
- `inbox/<session_id>.jsonl` — append-only per-session mailbox.
- `events.jsonl` — append-only audit/event log.

This ADR does not spawn agents. It only defines the shared state contract that ADR-235 can later consume.

## Implementation status (2026-05-07)

Implemented Slice A:

- `packages/agent-lifecycle/lib/agent_team.py` with `AgentTeam`, `TeamMember`, `TeamTask`, and `InboxMessage`.
- `lib/agent_team.py` package symlink.
- Advisory `fcntl` locks for member, task, inbox, and event writes.
- Task claim semantics that choose the first pending task whose dependencies are completed.
- Per-recipient inbox append/read.
- Unit and behavior tests proving membership, dependency-aware claims, duplicate-claim prevention, inbox delivery, and event log emission.

Not implemented yet:

- Hook consumers that call the library directly from `TaskCreated`, `TaskCompleted`, and `TeammateIdle`.
- CLI wrapper (`scripts/cos team ...`).
- Integration with ADR-230 handoff envelopes for team-to-team delegation.
- Cross-harness and chaos tests.
- Tier-3 NATS/A2A upgrade path.

## Hard rules

- Slice A is same-machine only.
- Writes use advisory locks; no read-modify-write JSON arrays.
- Inbox is append-only and at-least-once; consumers must treat message IDs as idempotency keys.
- Task claims must be locked and dependency-aware.
- No daemon, Redis, Postgres, NATS, or tmux dependency in the default path.

## Test matrix

- T1 unit: `tests/unit/test_agent_team.py`
- T3 behavior/contract: `tests/behavior/test_agent_team_file_ipc_flow.py`
- T4 smoke: covered by the behavior flow for two independent sessions
- T7 chaos: pending
- T8 cross-harness: pending

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_agent_team.py tests/behavior/test_agent_team_file_ipc_flow.py -q
```

The tests must prove:

- Sessions can join and be listed.
- Two sessions cannot claim the same pending task.
- Dependencies block claim until completed.
- Inbox messages append and read by recipient.
- Event log records membership, task, claim, completion, and message events.
