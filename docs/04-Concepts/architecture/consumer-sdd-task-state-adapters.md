# Consumer SDD Task-State Adapters

> Contract for mapping the local Consumer SDD Lane to external task systems without changing the lane semantics.

## Status

Contract accepted by ADR-322. Local JSON/Markdown is implemented. GitHub Issues,
Linear, and Jira are planned adapters and must not be built before the local
contract remains stable under real use.

## Canonical State Machine

All adapters map to these canonical states:

| Canonical state | Meaning |
|---|---|
| `pending` | Task exists but no durable spec has been drafted. |
| `spec_ready` | Requirements, design, and tasks are ready for human review. |
| `approved` | Human approved spec artifacts; implementation may begin. |
| `in_progress` | Implementation is underway against approved artifacts. |
| `review_ready` | Reviewer found missing evidence or drift; fixes required. |
| `done` | Review passed and history was appended. |
| `rejected` | Human rejected the task or spec. |

## Canonical Artifacts

Adapters must preserve or export these artifacts:

```text
requirements.md
design.md
tasks.md
traceability.md
review.md
progress/current.md
progress/history.md
```

External systems may link to these files, mirror their content, or attach them as
comments, but they must not become the only copy of the evidence.

## Adapter Interface

Every adapter must support:

| Operation | Requirement |
|---|---|
| `list_pending` | Return candidate tasks with stable IDs and titles. |
| `claim_one` | Select one active feature and prevent accidental parallel local work. |
| `write_artifacts` | Persist local SDD artifacts before implementation starts. |
| `transition` | Move between canonical states with actor, time, and reason. |
| `append_review` | Attach reviewer verdict and findings. |
| `append_history` | Preserve completed work in an append-only local history. |
| `export_local` | Recreate the local filesystem store from external state. |

## GitHub Issues Mapping

| Canonical field | GitHub Issues |
|---|---|
| Feature ID | issue number or stable slug label |
| Title | issue title |
| State | labels such as `sdd:spec-ready`, `sdd:approved`, `sdd:in-progress`, `sdd:review-ready`, `sdd:done` |
| Artifacts | committed files linked in issue comments or checked-list comments |
| Review | issue comment with `SDD_REVIEW` verdict |

GitHub adapter work is blocked until local mode has a contract test for export/import.

## Linear Mapping

| Canonical field | Linear |
|---|---|
| Feature ID | issue identifier, for example `ENG-123` |
| Title | issue title |
| State | team workflow states mapped to canonical states |
| Artifacts | links to committed local artifacts or comments containing artifact summaries |
| Review | comment with reviewer verdict and traceability summary |

Linear adapter work is blocked until the team chooses a canonical workspace/state
mapping. Do not hardcode one team's Linear workflow into Cognitive OS.

## Jira Mapping

| Canonical field | Jira |
|---|---|
| Feature ID | issue key, for example `PROJ-123` |
| Title | issue summary |
| State | project workflow statuses mapped through config |
| Artifacts | issue attachments or links to committed artifacts |
| Review | comment with reviewer verdict and residual risk |

Jira adapter work must require explicit project configuration because Jira
workflows vary heavily across organizations.

## Non-Goals

- Do not require any external adapter for the default local SDD proof.
- Do not store secrets or API tokens in the adapter config.
- Do not let an external task status bypass local review evidence.
- Do not relax the requirement-to-test/proof mapping for medium+ SDD work.

## Acceptance Criteria For Adapter Promotion

An adapter can move from planned to implemented only when:

1. it round-trips a task through local export/import;
2. it preserves all canonical artifacts;
3. it maps every external state to a canonical state;
4. it fails closed on unknown states;
5. it has tests that do not require live external credentials by default;
6. live API tests are opt-in and credential-safe.
