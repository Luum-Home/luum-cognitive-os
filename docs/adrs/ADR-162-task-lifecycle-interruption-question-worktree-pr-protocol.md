---

adr: 162
title: Task Lifecycle, Interruption, Question, Worktree, and PR Protocol
status: implemented
implementation_status: partial
classification_basis: 'implemented for contract scope; full queue/worker/PR runtime enforcement remains follow-up'
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

**Implemented for contract scope** — 2026-05-05. The task lifecycle schema, contract tests, and manual proof checklist exist; full queue/worker/PR runtime enforcement remains follow-up service-control-plane work.

## Context

ADR-161 separated remote ingress from provider/executor adapters. That boundary
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

## Operational Guide

### What changes for the operator

Before this ADR, there was no machine-readable contract for how tasks move through COS once admitted: how they pause, how agents ask questions, how interrupted work persists state, and how isolated work becomes a branch or PR. After this ADR:

- `manifests/task-lifecycle-schema.yaml` is the authoritative contract for task statuses, question types, interruption reasons, event communication, worktree ownership, and PR flow.
- Worktrees use `.worktrees/{task_id}` ownership; branches follow `codex/{task_id}-{slug}` naming.
- Agents ask questions as structured decision objects (not free-form chat): types include `requirement`, `approval`, `credential`, `conflict`, `product_decision`, `clarification`, `review`.
- Pull requests are the normal propose-only output for remote or headless work; direct publication actions are blocked by the contract.
- Remote and IDE-driven work now share the same lifecycle vocabulary.

Full queue/worker/PR runtime enforcement remains follow-up service-control-plane work; the contract exists and is tested before the daemon does.

### What this answers (and what it doesn't)

**Answers:**
- "What are the valid task statuses?" — read `manifests/task-lifecycle-schema.yaml`; statuses span `queued` → `running` → `waiting_for_human` → `interrupted` → `resumable` → `pr_ready` → `approved` → `merged` and terminal states.
- "How should an agent ask for operator input?" — use a structured question with a declared type and `blocking: true/false`; free-form chat messages are not interruption records.
- "Can an agent push directly to main?" — no; the contract blocks direct publication actions. PR flow is propose-only.

**Does not answer:**
- Whether the full queue/worker/PR runtime is implemented — that is follow-up `cosd` work. The contract governs vocabulary; enforcement needs the service-control-plane runtime.
- Whether a specific interruption reason is recoverable automatically — recovery policy is an operator decision; the schema defines the reason vocabulary, not the recovery action.

### Reading guide for cold readers

1. Read `manifests/task-lifecycle-schema.yaml` for the complete state-machine vocabulary.
2. Run `python3 -m pytest tests/contracts/test_task_lifecycle_schema.py -q` to verify required states, transitions, fields, and blocked publication actions.
3. Read `docs/manual-tests/task-lifecycle-worktree-pr-flow.md` for the manual proof checklist.
4. Read `docs/architecture/service-control-plane-implementation-plan.md` for how this contract fits the broader `cosd` plan.
5. Worktree naming (`codex/{task_id}-{slug}`) and the append-only event communication format are the two most commonly referenced invariants when debugging parallel-agent coordination.

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
  implement this contract incrementally without changing the vocabulary.
