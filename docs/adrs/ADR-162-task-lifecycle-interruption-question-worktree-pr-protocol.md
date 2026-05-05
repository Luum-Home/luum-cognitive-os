---
adr: 162
title: Task Lifecycle, Interruption, Question, Worktree, and PR Protocol
status: accepted
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - manifests/task-lifecycle-schema.yaml
  - docs/manual-tests/task-lifecycle-worktree-pr-flow.md
  - tests/contracts/test_task_lifecycle_schema.py
  - docs/architecture/service-control-plane-implementation-plan.md
tier: maintainer
tags: [task-lifecycle, interruptions, questions, worktrees, branches, pull-requests, cosd]
---

# ADR-162: Task Lifecycle, Interruption, Question, Worktree, and PR Protocol

## Status

**Accepted** — 2026-05-05

## Context

ADR-161 separated remote ingress from provider/executor adapters. That boundary
protects Cognitive OS from letting Telegram, Paperclip, webhooks, GitHub
comments, or IDE chat execute tools directly. The next missing contract is how
work moves through the SO once it has been admitted: how tasks pause, how agents
ask questions, how interruptions persist state, and how isolated work becomes a
branch or pull request.

The repository already has service-control-plane proof drills for local queue,
leases, crash/resume, and provider lab promotion. It also has a trust model that
requires human approval for publication, security-sensitive changes, and other
high-risk actions. However, the task lifecycle vocabulary was not yet fixed in a
machine-readable contract.

## Decision

Adopt `manifests/task-lifecycle-schema.yaml` as the initial contract for COS task
execution outside a single IDE session.

The contract defines:

- task statuses from `queued` through `running`, `waiting_for_human`,
  `interrupted`, `resumable`, `pr_ready`, `approved`, `merged`, and terminal
  states;
- structured questions with types such as `requirement`, `approval`,
  `credential`, `conflict`, `product_decision`, `clarification`, and `review`;
- interruption records with reasons such as `operator_interrupt`, `compaction`,
  `crash`, `auth_required`, `path_conflict`, `merge_conflict`, `policy_block`,
  and provider/rate/budget failures;
- append-only event communication for task state, questions, leases, validation,
  PRs, and completion;
- isolated worktree ownership using `.worktrees/{task_id}` and branch naming
  `codex/{task_id}-{slug}`;
- propose-only pull request flow with required body sections and blocked direct
  publication actions.

Agents may ask questions, but questions are decision objects, not hidden
free-form conversation. Interruptions are valid only after enough evidence is
persisted to resume or triage safely. Non-trivial implementation work should own
a task-scoped worktree, branch, lease, and claimed path set.

## Consequences

### Positive

- Remote and IDE-driven work share the same lifecycle vocabulary.
- Human interruptions and agent questions become auditable and resumable.
- Parallel agents can coordinate through claims, leases, worktrees, and branch
  ownership instead of relying on informal chat.
- Pull requests become the normal propose-only output for remote or headless
  work.
- The contract can be tested before a full `cosd` daemon exists.

### Negative

- The first implementation needs additional queue/event plumbing before the
  protocol is fully enforced.
- Small single-session tasks may feel heavier if every action is forced through
  the full lifecycle too early.
- Worktree cleanup must be conservative to avoid deleting recoverable work.
- Chat integrations need structured command and question handling before they
  are useful for complex build flows.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Let each IDE/CLI invent its own task states | Breaks portability and makes remote resume impossible. |
| Treat agent questions as plain chat messages | Loses blocking status, options, risk, and auditability. |
| Kill interrupted tasks without preserving worktree/branch/evidence | Makes crash/compaction/operator pause unsafe. |
| Let agents share one branch/worktree by default | Increases conflict risk and hides ownership. |
| Push directly to `main` from a worker | Violates the trust model and bypasses merge queue/human review. |
| Wait for a full daemon before defining the contract | Delays tests and lets ad-hoc behavior accumulate. |

## Verification

```bash
python3 -m pytest tests/contracts/test_task_lifecycle_schema.py -q
python3 -m pytest tests/audit/test_adr_contracts.py tests/audit/test_adr_locations.py -q
```

## Implementation Evidence

- `manifests/task-lifecycle-schema.yaml` defines the task/question/interruption
  communication/worktree/PR contract.
- `tests/contracts/test_task_lifecycle_schema.py` verifies required states,
  transitions, fields, event types, worktree naming, and blocked publication
  actions.
- `docs/manual-tests/task-lifecycle-worktree-pr-flow.md` records the manual proof
  checklist for this protocol.
- Future `cosd`, queue, worker, Telegram, Paperclip, GitHub, and PR adapters can
  implement this contract incrementally without changing the vocabulary.
