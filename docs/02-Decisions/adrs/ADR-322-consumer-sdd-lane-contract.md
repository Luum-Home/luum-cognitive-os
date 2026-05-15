---
adr: 322
title: Consumer SDD Lane Contract
status: accepted
implementation_status: partial
date: '2026-05-15'
supersedes: []
superseded_by: null
implementation_files:
- cmd/cos/internal/cli/sdd.go
- cmd/cos/internal/cli/sdd_test.go
- scripts/demo-consumer-sdd-lane.sh
- docs/09-Quality/manual-tests/consumer-sdd-lane.md
- docs/08-References/business/sdd-harness-consumer-workflow-audit.md
- docs/08-References/business/consumer-sdd-lane-surgical-review-plan.md
- docs/04-Concepts/architecture/consumer-sdd-task-state-adapters.md
tier: product
authority: local filesystem SDD lane, requirement-to-proof review gate, and cross-harness instruction projection
tags:
- sdd
- consumer-workflow
- task-state
- traceability
- portability
---

# ADR-322 — Consumer SDD Lane Contract

## Status

Accepted.

## Context

The comparison with `betta-tech/harness-sdd` exposed a product/workflow gap in
Cognitive OS. The repository already had strong SDD and EAS ingredients:
SDD skills, YAML workflows, EAS documentation, an EAS validator, and generic
traceability tooling. What it lacked was a consumer-facing happy path that a
new project can understand in minutes.

The missing operator story was:

```text
find task -> generate spec -> approve -> implement -> review against spec -> save evidence
```

Without this lane, Cognitive OS can feel like a governance mesh rather than a
workflow a consumer project can use tomorrow.

## Decision

Adopt a first-class **Consumer SDD Lane** as the default durable workflow for
medium or larger feature work in consumer projects.

The lane is local-filesystem-first and intentionally small:

```bash
cos sdd next --feature <slug> --title "<human title>"
cos sdd approve <slug>
cos sdd apply <slug>
cos sdd review <slug>
cos sdd status --json
```

The canonical local store is:

```text
.cognitive-os/workflows/sdd/state.json
.cognitive-os/workflows/sdd/<feature>/requirements.md
.cognitive-os/workflows/sdd/<feature>/design.md
.cognitive-os/workflows/sdd/<feature>/tasks.md
.cognitive-os/workflows/sdd/<feature>/traceability.md
.cognitive-os/workflows/sdd/<feature>/review.md
.cognitive-os/workflows/sdd/progress/current.md
.cognitive-os/workflows/sdd/progress/history.md
```

The local state machine is:

```text
pending -> spec_ready -> approved -> in_progress -> review_ready|done
```

The lane enforces one active local feature at a time for simple consumer
projects. This is a deliberate safety default, not a claim that all future
adapters must serialize all work.

## Proportionality Policy

The lane is not mandatory for every task.

| Work class | Default workflow |
|---|---|
| Trivial | Direct change plus minimal verification. |
| Small | Brief plan plus existing tests or focused checks. |
| Medium | Consumer SDD lane with requirements/design/tasks/traceability/review. |
| Large | Consumer SDD lane plus EAS recommended or required by project policy. |
| Critical | Consumer SDD lane plus EAS, human approval, audit trail, rollback/security/idempotency checks. |

ADR-014's model-based fast path must not override this risk policy. A capable
model may reduce internal planning overhead, but it must not skip durable spec
and evidence artifacts when the work class requires them.

## Review Gate

`cos sdd review` is a narrow evidence gate, not a generic quality vibe. It fails
when:

- a requirement ID such as `R1` has no test or accepted proof mapping;
- `tasks.md` still contains unchecked tasks;
- `traceability.md` still contains placeholder evidence;
- `design.md` still contains placeholder implementation boundaries.

A review can pass only when every requirement maps to concrete test evidence or
an explicit accepted manual proof.

## Cross-Harness Projection

The source of truth is the canonical lane contract and CLI behavior, not a
Claude-only prompt file.

Projection rules:

- Claude receives the lane in `.claude/CLAUDE.md` through `templates/CLAUDE.md.template`.
- Structural harnesses receive the lane in their generated instruction body via
  `scripts/cos_init.py`.
- Native lifecycle parity is not claimed unless a harness-specific runtime proof
  exists.

## External Task-State Adapters

GitHub Issues, Linear, and Jira are accepted as planned adapters, but they must
not change the canonical lane semantics. They map external ticket state to the
same local contract and must preserve local artifact export.

The adapter contract is documented in
`docs/04-Concepts/architecture/consumer-sdd-task-state-adapters.md`.

## Consequences

Positive:

- Cognitive OS now has a concrete consumer happy path.
- The workflow reuses SDD/EAS ingredients instead of creating a new workflow engine.
- Local mode works without external APIs, dashboards, or task systems.
- Requirement-to-proof traceability becomes visible and enforceable.

Tradeoffs:

- The first implementation is intentionally local-only.
- External adapters remain design/contract work until local behavior proves stable.
- One-active-feature is conservative and may need adapter-specific relaxation later.

## Alternatives rejected

- Leave the decision implicit in conversation history: rejected because ADR-gated governance needs a durable, reviewable record with explicit trade-offs.
- Treat this as an unversioned implementation note: rejected because the behavior affects operator-facing contracts and must survive refactors.

## Verification

```bash
cd cmd/cos && go test ./internal/cli -run 'TestE2E_SDD' -count=1
bash scripts/demo-consumer-sdd-lane.sh
.venv/bin/python -m pytest tests/behavior/test_consumer_project_projection.py -k 'default_install_projects_core_primitives and agents-md' -q
.venv/bin/python -m pytest tests/integration/test_installer.py -k 'new_claude_repo_local_source_install_smoke' -q
```
