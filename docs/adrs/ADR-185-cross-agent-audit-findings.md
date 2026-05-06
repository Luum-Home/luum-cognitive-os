---
adr: 185
title: Cross-Agent Audit Findings Queue — Auditor → Implementer Directive Channel
status: accepted
date: 2026-05-05
supersedes: []
superseded_by: null
extends: []
implementation_files:
  - lib/agent_message_bus.py                 # v1 directed message queue
  - scripts/cos_agent_message.py             # v1 CLI
  - scripts/cos-agent-message                # v1 wrapper
  - hooks/agent-message-inbox-guard.sh       # v1 severity gate
  - tests/unit/test_agent_message_bus.py     # v1 tests
  - hooks/agent-message-inbox-context.sh      # v1 UserPromptSubmit inbox context
  - tests/unit/test_agent_message_hooks.py    # v1 hook tests
  - .cognitive-os/coordination/agent-messages.jsonl # runtime artifact
  - packages/agent-lifecycle/lib/harness_adapter/base.py # companion inbound_signal event
  - packages/agent-lifecycle/lib/harness_adapter/dispatch.py # companion inbound signal dispatch
  - lib/agent_control_policy.py              # portable stop/pause/resume policy
  - hooks/agent-control-inbound-guard.sh     # hook-boundary enforcement for non-owned processes
tier: maintainer
tags: [concurrency, governance, agent-coordination, postmortem-2026-05-05, companion-ADR-182-183-184]
---
# ADR-185: Cross-Agent Audit Findings Queue — Auditor → Implementer Directive Channel

## Status

**Accepted.** Implemented as the directed message bus, inbox/context hooks, CLI, and tests. Fourth architectural layer companion to ADR-182 (branch
ownership lock), ADR-183 (cross-session event log), and ADR-184
(manager-of-managers daemon). Where the previous three address
*conflict prevention*, *peer awareness*, and *single-writer authority*,
ADR-185 addresses **directive flow**: how an auditor agent's findings
reach the implementer agent that needs to act on them.

## Context

The 2026-05-05 cross-session collision incident
(`docs/reports/postmortem-cross-session-collision-2026-05-05.md`)
exposed structural concurrency gaps. ADRs 182–184 address the gaps at
the lock / awareness / authority layers. A residual gap remains:

> When an auditor agent finds a defect that an implementer agent must
> fix, **how does the finding reach the implementer reliably**?

Today the answer is informal:

- Auditor calls `mem_save` (Engram). Implementer **must** call
  `mem_search` to find it. **Polling-based; if no one searches, no one
  sees.**
- Auditor writes a `docs/reports/<date>.md` file. Implementer must
  open and read it. **Async, requires intentional reading.**
- Auditor logs to `.cognitive-os/metrics/<x>.jsonl`. No standard
  consumer. **Audit trail only.**
- Agent Bus / Valkey pub-sub exists but is per-session, mostly OFF.

The gap is **directive semantics**: today's primitives carry
information but not *intent that someone act*. A finding is treated as
optional context rather than as a directive that must be consumed
before related work proceeds.

ADR-183's generic event log informs peers but does not have severity
gating, target filtering, or consumed/resolved state. Findings sit
alongside `commit-intent` and `agent-spawn` events without distinction.

## Decision

Adopt the implemented **typed, severity-graded, append-only directed message
queue** as ADR-185 v1. The v1 implementation is intentionally named
`agent_message_bus` because it carries audit findings plus implementation
requests, questions, replies, and status messages.

The queue:

1. Lets any agent emit a finding with structured metadata.
2. Surfaces unresolved directed findings through an inbox CLI and future
   UserPromptSubmit context hook.
3. Gates risky Bash/git boundaries at `severity=block` via
   `agent-message-inbox-guard.sh`.
4. Tracks acknowledgement state explicitly through append-only ack entries.
5. Lives at `.cognitive-os/coordination/agent-messages.jsonl` (per-machine,
   append-only).

### Finding schema

```json
{
  "schema_version": 1,
  "kind": "message",
  "message_id": "d4c0b9f2a8e13744",
  "timestamp_epoch": 1778012502.123,
  "from_session": "auditor-session",
  "to_session": "operator-session",
  "role": "auditor",
  "message_type": "audit_finding",
  "severity": "block",
  "target": "lib/skill_router.py:84-96",
  "body": "Two routing entries reference skills absent from disk.",
  "metadata": {
    "recommended_fix": "Remove orphan entries or add an allowlist rationale.",
    "evidence": "git grep ...; ls ..."
  }
}
```

Severity semantics:

- **block** — blocks the targeted session at risky Bash/git boundaries until
  acknowledged.
- **warn** — surfaced in inbox and context, but does not block.
- **info** — informational only.

### Emission API

```python
from lib.agent_message_bus import send_message

send_message(
    project_dir,
    from_session="auditor-session",
    to_session="operator-session",
    message_type="audit_finding",
    severity="block",
    target="lib/skill_router.py:84-96",
    body="Two routing entries reference skills absent from disk.",
    metadata={"recommended_fix": "...", "evidence": "..."},
)
```

Auditor agents are encouraged to persist a durable Engram summary when the
`mem_*` tools are available, but the runtime queue must not depend on Engram
availability.

### Consumption flow

1. **Inbox check**:
   - `scripts/cos-agent-message inbox --session-id <operator-session>`
   - shows unacknowledged messages for that target session.

2. **PreToolUse Bash hook** `agent-message-inbox-guard.sh`:
   - checks messages with `severity=block` targeting the current session;
   - if any are unacknowledged: warns by default, blocks under
     `COS_AGENT_MESSAGE_GUARD_MODE=block`.

3. **Acknowledgement API**:
   ```python
   from lib.agent_message_bus import ack_message
   ack_message(project_dir, message_id_value="<id>", session_id="operator", status="applied")
   ```
   The append-only log gets a follow-up ack entry. Readers stitch state by
   `message_id`.

4. **Future context hook**:
   - a UserPromptSubmit context injector may summarize pending messages, but the
     v1 accepted path is the inbox CLI plus Bash/git guard.

### Engram cross-write

When Engram tools are available, message emission may also persist a summary
under topic key `audit-findings/<message-id>`. This is best-effort, not a
hard runtime dependency, because Codex/Claude environments do not always expose
the same `mem_*` tools.

The JSONL is the **runtime queue**; Engram is an optional **archive**.

## Acceptance Criteria

1. `lib/agent_message_bus.py` exposes `send_message`, `inbox`,
   `ack_message`, `unacked_blockers`, and `blocker_findings`.
2. `scripts/cos-agent-message` exposes send/inbox/ack/check.
3. `hooks/agent-message-inbox-guard.sh` is registered as a PreToolUse Bash
   guard through `scripts/_lib/settings-driver-claude-code.sh`.
4. `tests/unit/test_agent_message_bus.py` covers:
   - send + inbox round-trip;
   - severity filtering;
   - ack state stitching from append-only log;
   - blocking check before and after ack.
5. Operator strict-mode env var `COS_AGENT_MESSAGE_GUARD_MODE=block` is
   documented.
6. Runtime JSONL path `.cognitive-os/coordination/agent-messages.jsonl` remains
   under ignored runtime state.
7. Engram archive write is best-effort when tools are available, not a blocking
   acceptance criterion.

## Border Cases

- **Auditor finding targets a session that has already ended**:
  finding stays pending; the next session that matches the filter
  consumes it. TTL of 30 days; older findings auto-archive.
- **Auditor and implementer are the same agent in the same session**:
  legal but pointless; emit warning ("self-directed finding — consider
  inline fix instead").
- **Multiple auditors emit the same finding**: deduped by `subject` +
  `evidence` content hash.
- **Implementer marks consumed without actually fixing**: detected by
  later auditor re-running same check; new finding cites the prior
  consumed-but-unresolved id and escalates severity.
- **JSONL grows unbounded**: rotated at 50 MB; archived to
  `.cognitive-os/coordination/agent-messages-archive/<YYYY-MM>.jsonl.gz`.
- **Operator wants a clean queue**: future maintenance tooling may archive
  acknowledged low-severity entries without deleting unresolved blockers.

## Companion Inbound Signal Protocol

ADR-185 remains the directed, append-only **agent-to-agent** directive queue. A 2026-05-06 follow-up adds a companion **orchestrator-to-agent** inbound signal protocol at the harness-adapter layer. It does not replace ADR-185; it gives runtime loops a canonical way to observe Agent Bus fallback controls and clarification answers.

The companion event is `event_type: "inbound_signal"` and is emitted by `packages/agent-lifecycle/lib/harness_adapter/dispatch.py` after normal outbound event parsing. It carries:

- `signal_type`: `control`, `answer`, or `interrupt`;
- `command`: `stop`, `pause`, or `resume` for control signals;
- `answers` and `round` for clarification answers;
- `agent_id` / `session_id` when the adapter can infer the target;
- `source_path` for the fallback artifact that produced the signal.

This keeps ADR-185's store-and-forward directive queue separate from mid-flight control, while giving both paths a shared canonical-event surface. Runtimes with a child process handle can enforce controls directly. Hook-capable runtimes without a process handle use `agent-control-inbound-guard.sh`, which blocks on latest `stop` or unresolved `pause` and allows execution again after a newer `resume`. Runtimes without hooks should call `lib.agent_control_policy.evaluate_control()` before each action.

## Consequences

### Positive

- Tonight's pattern (auditor finds bug, implementer doesn't see it)
  becomes structurally addressable: auditor emits → next orchestrator
  on the matching scope sees it injected into context → must consume
  before commit (if blocking).
- Provides a typed channel that complements (not replaces)
  Engram-as-archive.
- Decouples "finding produced" from "finding read": the polling burden
  shifts from the implementer-by-search to the hook-by-injection.
- Operator gains a backlog of unresolved findings as a first-class
  artifact.

### Negative

- New JSONL file to manage and rotate.
- Adds latency to every UserPromptSubmit (~50 ms typical) and to every
  commit (~10 ms).
- Risk of finding spam if low-severity emit is overused; mitigated by
  severity filtering at hook level and dedup at emit level.
- Per-machine only in v1; cross-machine requires Engram Cloud
  federation (ADR-136).

### Neutral

- Engram remains the durable cross-session memory; this is the
  *transient queue* layer.

## Alternatives rejected

- **Use Engram alone with a strict topic_key naming convention**:
  works but loses severity gating + commit blocking. Rejected as
  primary; Engram remains the archive.
- **Reuse ADR-183 cross-session events with a `kind: audit-finding`
  variant**: violates separation. ADR-183 is generic infrastructure
  events; ADR-185 is directive semantics. Mixing them dilutes both.
  Rejected.
- **GitHub Issues / external ticketing**: too heavy for per-machine
  operator workflow. Rejected for v1; useful for team-scale later.
- **Slack / external notification**: same as above.

## Falsifiable Claim

ADR-185 is correct if, in a 90-day audit window after adoption:

1. **Detection rate**: ≥ 95 % of unresolved findings emitted by
   auditor agents are surfaced to a subsequent matching orchestrator
   within one prompt cycle.
2. **Severity-gate efficacy**: zero commits land while a critical or
   high+blocks_commit finding is unresolved on the target branch
   (override usage tracked separately).
3. **False positive rate**: < 5 % of findings are marked consumed
   with `resolution: false-positive` (high false-positive rate would
   indicate the auditor heuristics need tuning, not that the channel
   is broken).
4. **Latency**: 99th percentile UserPromptSubmit hook latency stays
   < 200 ms even with 100+ pending findings in the queue.

If any of (1), (2), or (4) fail at the threshold, ADR-185 must be
revisited. (3) is informational about auditor quality, not channel
quality.

## Cross-References

- `docs/reports/postmortem-cross-session-collision-2026-05-05.md` —
  origin incident.
- ADR-182 — branch ownership lock (companion: ADR-182 prevents two
  writers; ADR-185 routes findings between sequential writers).
- ADR-183 — cross-session event log (companion: ADR-183 is generic
  events; ADR-185 is directive findings).
- ADR-184 — manager-of-managers daemon (when present, daemon consumes
  ADR-185 queue alongside ADR-183 to make global decisions; without
  daemon, hooks alone are sufficient).
- ADR-088 — commit_provenance attribution (compatible: findings
  reference commit SHAs and X-COS-Origin metadata).
- ADR-134 — propose-only self-improvement (audit-finding semantics
  align with propose-only: auditor proposes, implementer/operator
  decides).
- ADR-136 — cross-instance learning runway (future: findings
  federate via Engram Cloud).
- `docs/architecture/agent-message-bus.md` — implemented v1 contract.
- `manifests/session-coordination-contract.yaml` — machine-readable contract.
- Engram `mem_*` tools — optional durable archive when surfaced by the active
  harness.

## Open questions

- Whether to expose the queue to sub-agents directly (so a sub-agent
  can read pending findings before starting work). Proposed: yes,
  via the same hook injection pattern at SubagentStart. Decision
  deferred to implementation phase.
- Whether to gate `Agent` tool launches (not just commits) when a
  critical finding is pending on the target scope. Proposed: yes for
  critical only; defer until soak data confirms detection works.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

