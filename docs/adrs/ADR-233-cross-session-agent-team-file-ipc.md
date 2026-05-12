---
adr: 233
title: Cross-Session Agent-Team File IPC
status: accepted
implementation_status: implemented
date: '2026-05-07'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit accepted/implemented status
---

# ADR-233 — Cross-Session Agent-Team File IPC

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted — Slices A–C implemented (2026-05-07)  
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

Implemented Slice B:

- `scripts/cos-team` plus `cos team ...` dispatch for membership, task lifecycle, messages, inbox reads, and handoff sends.
- `TaskCreated` optionally mirrors tasks into `.cognitive-os/teams/<team>/tasks.jsonl` when `team_name`/`team` or `COS_AGENT_TEAM_NAME` is provided.
- `TeammateIdle` optionally claims the next dependency-ready team task before falling back to legacy `.claude/tasks/active-tasks.json`.
- ADR-230 handoff envelopes can now be delivered as at-least-once inbox messages through ADR-233 file IPC.

Implemented Slice C:

- `TaskCompleted` optionally mirrors completion into `AgentTeam.complete_task`.
- Chaos test proves `claim_next` has a single winner across concurrent processes.
- Cross-harness contract test proves Codex-style and Claude-style session envs share the same team inbox/handoff transport.

Implemented Slice D:

- Receiver execution is consumed through ADR-230 `cos team handoff receive`, including external hook command execution and idempotency receipts.
- `lib/agent_team_transport.py` and `cos team transport-plan` expose a machine-readable file/NATS/A2A upgrade mapping without adding NATS/A2A dependencies to the default install.

Implemented Slice E:

- `NatsAgentTeamTransport` publishes ADR-233 inbox payloads to NATS subjects using an injected/optional `nats-py` client. `connect()` is opt-in and raises a clear install error if `nats-py` is absent.
- `A2AHttpAgentTeamTransport` POSTs schema-versioned A2A-style JSON message envelopes to an operator-provided HTTP endpoint using stdlib `urllib`.
- `cos team transport-send` exposes A2A HTTP send and NATS dry-run planning; NATS live clients are consumed through the Python adapter to avoid a default dependency.

## Hard rules

- Slice A is same-machine only.
- Writes use advisory locks; no read-modify-write JSON arrays.
- Inbox is append-only and at-least-once; consumers must treat message IDs as idempotency keys.
- Task claims must be locked and dependency-aware.
- No daemon, Redis, Postgres, NATS, A2A SDK, or tmux dependency in the default path.

## Test matrix

- T1 unit: `tests/unit/test_agent_team.py`
- T3 behavior/contract: `tests/behavior/test_agent_team_file_ipc_flow.py`
- T4 smoke: covered by the behavior flow for two independent sessions
- T7 chaos: `tests/chaos/test_agent_team_claim_race.py`
- T8 cross-harness: `tests/integration/test_agent_team_cross_harness_contract.py`
- Upgrade-path + adapters: `tests/unit/test_agent_team_transport.py` and `tests/behavior/test_cos_team_cli.py::test_cos_team_transport_plan_cli_exposes_nats_upgrade_mapping`, `test_cos_team_transport_send_a2a_http_posts_message`, `test_cos_team_transport_send_nats_dry_run_plan`

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_agent_team.py tests/unit/test_agent_team_transport.py tests/behavior/test_agent_team_file_ipc_flow.py tests/behavior/test_cos_team_cli.py tests/hooks/test_agent_team_file_ipc_hooks.py -q
```

The tests must prove:

- Sessions can join and be listed.
- Two sessions cannot claim the same pending task.
- Dependencies block claim until completed.
- Inbox messages append and read by recipient.
- Event log records membership, task, claim, completion, and message events.

## Consequences
- The ADR can be checked by the common ADR contract audit.
- Future amendments must preserve this decision record instead of relying on conversation history.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
