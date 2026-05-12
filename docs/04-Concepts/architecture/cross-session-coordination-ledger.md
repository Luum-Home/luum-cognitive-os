---
title: Cross-Session Coordination Ledger
date: 2026-05-05
status: active
tags: [coordination, worktree, adr, session, primitive]
---

# Cross-Session Coordination Ledger

## Problem

Parallel agents can share a repository without sharing intent. Git exposes
files, commits, branches, and worktrees, but it does not know that a session has
reserved `ADR-171`, that a sibling worktree is being reviewed read-only, or that
one branch chose `deprecated/archived` while another chose `delete/tombstone`.

The failure mode is especially sharp across IDEs and harnesses. Codex, Claude
Code, Cursor, and other surfaces keep separate conversation state. Even two
sessions in the same IDE can reason as if their local context is complete.

## Contract

The SO now treats cross-session intent as a local runtime ledger:

- claims live in `.cognitive-os/coordination/session-claims.json`;
- worktree intake records live in `.cognitive-os/coordination/worktree-intake.json`;
- directed auditor/operator messages live in `.cognitive-os/coordination/agent-messages.jsonl`;
- policy is documented in `manifests/session-coordination-contract.yaml`;
- deterministic checks live in `lib/session_coordination.py`;
- operators and hooks use `scripts/cos-session-coordination` and
  `scripts/cos-agent-message`.

The ledger is not a replacement for git. It is the semantic layer that git does
not provide.

## Claim types

| Kind | Example | Blocks |
|---|---|---|
| `task` | `paperclip-disposition` | duplicate task ownership |
| `adr-number` | `ADR-171` | ADR number reuse or tombstone collision |
| `path` | `docs/adrs/ADR-171-reject-paperclip-integration.md` | exact path ownership collision |
| `policy` | `paperclip-disposition` | incompatible cleanup policy work |
| `skill` | `adr-tombstone` | duplicate skill creation |
| `primitive` | `cross-session-coordination` | duplicate agentic primitive work |

## Operator flow

Reserve ADR intent before writing or tombstoning:

```bash
scripts/cos-session-coordination claim \
  --kind adr-number \
  --subject ADR-171 \
  --session-id "${COGNITIVE_OS_SESSION_ID:-manual}"
```

Record sibling worktree intake before importing or ignoring another branch:

```bash
scripts/cos-session-coordination record-worktree-intake \
  --other-worktree /path/to/sibling-worktree \
  --policy read-only \
  --summary "Audited branch state only; no import approved."
```

Check whether an ADR can be tombstoned:

```bash
scripts/cos-session-coordination check-adr-tombstone --number 171
```

List active claims:

```bash
scripts/cos-session-coordination list
```

## Auditor to operator message flow

An auditor may inspect branches, worktrees, logs, docs, tests, and diffs. The
auditor must not mutate the operator's branch unless explicitly promoted to an
operator role. Instead, the auditor sends directed messages.

Send a blocking audit finding:

```bash
scripts/cos-agent-message send \
  --from-session auditor-session \
  --to-session operator-session \
  --type audit_finding \
  --severity block \
  --target docs/adrs/ADR-171-tombstone.md \
  --body "ADR-171 is semantically owned by the Paperclip rejection decision; do not tombstone it."
```

Read the operator inbox:

```bash
scripts/cos-agent-message inbox --session-id operator-session
```

Acknowledge after applying, accepting, rejecting, or requesting clarification:

```bash
scripts/cos-agent-message ack \
  --message-id <id> \
  --session-id operator-session \
  --status applied \
  --note "Restored ADR-171 decision and removed conflicting tombstone."
```

Check for unacknowledged blocking messages:

```bash
scripts/cos-agent-message check --session-id operator-session
```

Valid acknowledgement statuses:

| Status | Meaning |
|---|---|
| `seen` | Operator received it, no decision yet |
| `accepted` | Operator agrees and will apply |
| `applied` | Operator applied the requested fix |
| `rejected` | Operator intentionally rejected it |
| `needs-clarification` | Operator needs a narrower request |

Blocking messages are about coordination, not authority. A rejected finding is
allowed, but it becomes auditable history rather than silent divergence.

## Hook behavior

`hooks/cross-session-coordination-guard.sh` runs at Bash/git boundaries through
the settings driver. It is advisory by default:

```bash
COS_SESSION_COORDINATION_MODE=warn
```

Strict mode blocks missing sibling-worktree intake:

```bash
COS_SESSION_COORDINATION_MODE=block
```

The default stays advisory because reconstruction sometimes needs quick local
repair, but the strict switch exists for high-risk multi-agent sessions.

`hooks/agent-message-inbox-guard.sh` checks the current session's inbox for
unacknowledged `severity=block` messages. It is advisory by default:

```bash
COS_AGENT_MESSAGE_GUARD_MODE=warn
```

Strict mode blocks risky Bash/git boundaries until the target session acks:

```bash
COS_AGENT_MESSAGE_GUARD_MODE=block
```

## ADR tombstone rule

`scripts/adr_tombstone.py` now refuses to replace active ADR files by default.
This prevents a neutral tombstone from silently erasing a number already owned
by another session. Replacing active prose requires an explicit
`--force-replace-active` flag and should only happen after an intake record and
operator decision.

## What this prevents

The Paperclip/routing incident had this shape:

```text
session A: routing + deprecated/archived Paperclip policy
session B: purge + tombstone Paperclip policy
no shared claim ledger
no ADR number ownership check
no worktree intake record
=> same branch carried both policies
=> ADR-171/173/179 became tombstones despite active semantic ownership
```

With this contract:

- `ADR-171` can be claimed before writing;
- tombstoning `ADR-171` fails if an active ADR file exists or another session
  claims the number;
- sibling worktrees are visible as requiring intake before risky git actions;
- auditors send blocking findings to the operator inbox instead of patching the
  operator branch directly;
- operators acknowledge findings before commit/push boundaries;
- the manager/orchestrator role has a shared ledger rather than private
  conversational memory.

## Acceptance

```bash
python3 -m pytest tests/unit/test_session_coordination.py tests/unit/test_adr_tombstone.py -q
python3 -m pytest tests/unit/test_agent_message_bus.py -q
bash -n hooks/cross-session-coordination-guard.sh hooks/agent-message-inbox-guard.sh
```
