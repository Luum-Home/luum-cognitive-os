---
title: Agent Message Bus
date: 2026-05-05
status: active
tags: [coordination, agents, audit, inbox, ack]
---

# Agent Message Bus

## Purpose

Provide a directed communication channel between agents that may run in
different IDE sessions but share the same repository filesystem.

The bus solves a specific coordination gap: an auditor should be able to review
another branch or worktree and ask the operator to adjust implementation without
mutating the operator's files.

## Storage

Messages are append-only JSONL:

```text
.cognitive-os/coordination/agent-messages.jsonl
```

Writes are guarded by:

```text
.cognitive-os/coordination/agent-messages.lock
```

Each sent message also emits a coarse event through the existing session event
bus so status tools can observe traffic without parsing full message bodies.

## Roles

| Role | Allowed behavior |
|---|---|
| Auditor | Read, compare, send findings/requests/questions |
| Operator | Apply, reject, ask for clarification, ack |
| Manager | Maintain claims, worktree intake, routing of messages |

An auditor is not an operator. Audit output travels through the message bus.

## CLI

Send:

```bash
scripts/cos-agent-message send \
  --from-session auditor \
  --to-session operator \
  --type audit_finding \
  --severity block \
  --target docs/adrs/ADR-171-tombstone.md \
  --body "ADR-171 collides with active session ownership."
```

Inbox:

```bash
scripts/cos-agent-message inbox --session-id operator
```

Ack:

```bash
scripts/cos-agent-message ack \
  --message-id <id> \
  --session-id operator \
  --status applied \
  --note "Removed conflicting tombstone."
```

Gate:

```bash
scripts/cos-agent-message check --session-id operator
```

## Enforcement

`hooks/agent-message-inbox-guard.sh` checks for unacknowledged blocking messages
at Bash/git boundaries.

Default:

```bash
COS_AGENT_MESSAGE_GUARD_MODE=warn
```

Strict:

```bash
COS_AGENT_MESSAGE_GUARD_MODE=block
```

## Contract

- Blocking messages require acknowledgement.
- Acknowledgement can be `seen`, `accepted`, `applied`, `rejected`, or
  `needs-clarification`.
- Rejection is valid but explicit; silent divergence is not.
- The bus is local-filesystem scoped. Cross-machine delivery needs a future
  transport over Engram Cloud or another synchronization layer.
