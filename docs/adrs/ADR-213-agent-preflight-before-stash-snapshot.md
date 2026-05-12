---
adr: 213
title: Agent Preflight Before Stash Snapshot
status: accepted
implementation_status: implemented
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation/shipped/delivered evidence
---

# ADR-213 — Agent Preflight Before Stash Snapshot

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted  
**Date**: 2026-05-06  
**Related**: ADR-117, ADR-199, ADR-200  
**Source**: `docs/reports/stash-hidden-wip-postmortem-2026-05-06.md`

---

## Context

Cognitive OS uses `pre-agent-snapshot.sh` to preserve the operator working tree
before launching sub-agents. The snapshot path may create an `auto-pre-agent-*`
git stash for tracked modifications. `post-agent-snapshot-restore.sh` restores
that stash after the Agent tool completes.

A failure mode was observed: the snapshot hook ran before a blocking launch
preflight (`agent-prelaunch.sh`). When the later preflight blocked, the Agent
tool never launched and the PostToolUse restore hook never fired. Real operator
WIP moved from the working tree into an `auto-pre-agent-*` stash and appeared to
be missing until manual stash forensics recovered it.

## Decision

All **blocking Agent preflight hooks** must run before any hook that mutates git
stash or hides working-tree content.

`pre-agent-snapshot.sh` is a mutation-preservation hook, not a launch admission
gate. Therefore it must run after:

- dispatch/admission gates;
- capability-contract preflight;
- ADR-116 work inventory / task claim preflight (`agent-prelaunch.sh`);
- any other blocker that can return exit 2 before the Agent starts.

If a preflight blocks, no snapshot stash should have been created. If a snapshot
stash exists, the Agent launch must have passed the blocking preflight boundary
or the restore path must be guaranteed to run.

## Enforcement

The hook order in active Claude settings, security profile templates, and the
settings generator must place `agent-prelaunch.sh` before
`pre-agent-snapshot.sh`.

A unit contract test verifies this invariant for:

- `.claude/settings.json`;
- `templates/security-profiles/standard.json`;
- `templates/security-profiles/paranoid.json`;
- `scripts/_lib/settings-driver-claude-code.sh`.

## Consequences

### Positive

- A blocked launch can no longer hide WIP in an auto-pre-agent stash.
- ADR-199/200 stash reapers stay cleanup tools, not recovery from a preventable
  launch-order bug.
- Operator trust improves: preflight blocks do not mutate the working tree.

### Negative / trade-offs

- If `agent-prelaunch.sh` itself needs a snapshot someday, that must be a
  separate explicit preflight snapshot with restore-on-block semantics.
- The snapshot occurs slightly later in the hook chain, after preflight gates
  have done read-only/ledger work.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_agent_hook_order.py tests/behavior/test_agent_blocked_preflight_no_stash.py -q
python3 -m pytest tests/unit/test_codex_guard_layer.py::test_pre_agent_snapshot_runs_after_blocking_agent_gates -q
```

Both active harness projection and generated Claude settings must prove
`agent-prelaunch.sh` precedes `pre-agent-snapshot.sh`.

The smoke test must simulate a dirty working tree plus a manual stash that makes
`agent-prelaunch.sh` block. In the correct order, no `auto-pre-agent-*` stash is
created and the dirty working-tree diff remains visible. A control test proves
the old snapshot-before-preflight order would have hidden that WIP in stash.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
