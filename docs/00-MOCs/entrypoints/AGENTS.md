# AGENTS.md — AI-Agent Routing Guide

Human-curated. <150 lines. Do not auto-generate or overwrite.

## Intent-based entrypoints (MOCs)

When you don't yet know which file to read, start at the right **Map of Content**:

- [`00-MOCs/decisions.md`](00-MOCs/decisions.md) — anything ADR-related
- [`00-MOCs/architecture.md`](00-MOCs/architecture.md) — designing or understanding components
- [`00-MOCs/workflow.md`](00-MOCs/workflow.md) — SDD pipeline, sprints, agent orchestration
- [`00-MOCs/quality.md`](00-MOCs/quality.md) — tests, gates, security, compliance
- [`00-MOCs/operations.md`](00-MOCs/operations.md) — incidents, releases, capabilities
- [`00-MOCs/onboarding.md`](00-MOCs/onboarding.md) — first time on this project

Use the routing table below for task types where the entrypoint is obvious.

---

## Task-to-Doc Routing Table

| Task type         | Read first                        | Then (if needed)                        |
|-------------------|-----------------------------------|-----------------------------------------|
| Bug fix           | `docs/02-Decisions/adrs/` (relevant ADR)       | `docs/06-Daily/reports/` (incident/forensics)    |
| New feature       | `docs/04-Concepts/architecture-principles.md` | `docs/02-Decisions/adrs/`, `docs/07-Capabilities/skills/`            |
| ADR write         | `docs/02-Decisions/adrs/ADR-NNN-slug.md` (latest example) | `docs/04-Concepts/architecture.md`         |
| Performance work  | `docs/04-Concepts/root/performance.md`             | `docs/06-Daily/reports/` (benchmarks), `docs/08-References/benchmarks/` |
| Security review   | `docs/04-Concepts/root/security-stack.md`          | `docs/compliance/`, `docs/09-Quality/security/`   |
| Release           | `docs/01-Build-Log/release/`                   | `docs/01-Build-Log/root/versioning-strategy.md`           |
| Testing / QA      | `docs/09-Quality/root/testing.md`                 | `docs/09-Quality/quality/`, `docs/09-Quality/manual-tests/`  |
| Skill authoring   | `docs/07-Capabilities/skills/`                    | `rules/RULES-COMPACT.md` §11           |
| Hook authoring    | `docs/05-Methodology/root/hooks.md`                   | `rules/RULES-COMPACT.md` §10           |
| Research / report | `docs/06-Daily/reports/` (newest relevant) | `templates/agent-research-only.md`     |

---

## Canonical Terms Glossary

| Term            | Definition                                                                 |
|-----------------|----------------------------------------------------------------------------|
| **COS**         | Cognitive Operating System — this repo; the AI-agent orchestration layer   |
| **ADR**         | Architecture Decision Record; lives at `docs/02-Decisions/adrs/ADR-NNN-slug.md`        |
| **primitive**   | Atomic capability unit (a single skill step or tool wrapper)               |
| **harness**     | The IDE/CLI shell hosting the agent (Claude Code, Cursor, Aider, etc.)     |
| **SDD**         | Spec-Driven Development; the repo's change workflow (explore→propose→apply→verify→archive) |
| **skill**       | A named, versioned prompt file that extends agent capabilities             |
| **engram**      | Persistent memory backend used across sessions via `mem_save`/`mem_search` |
| **hook**        | Shell script triggered by harness events (pre-commit, post-task, etc.)     |
| **phase**       | Project maturity mode: reconstruction / production (affects governance)    |
| **DAG**         | Directed Acyclic Graph; SDD dependency graph between phases                |
| **DoD**         | Definition of Done; 5-level quality checklist (`docs/05-Methodology/root/definition-of-done.md`) |
| **blast radius**| Estimated scope of a change (files touched, services affected)             |
| **tombstone**   | An ADR marked superseded/withdrawn; file kept for history                  |
| **lane**        | Test isolation group; registry at `.cognitive-os/test-lanes.yaml`          |
| **cosd**        | COS daemon; remote API requiring `--allow-remote` + bearer auth            |

---

## Report Naming Convention

```
docs/06-Daily/reports/<topic>-YYYY-MM-DD.md
```

Examples: `docs/06-Daily/reports/aspirational-audit-2026-05-08.md`, `docs/06-Daily/reports/ai-agent-harness-landscape-2026-05-04.md`

- Topic slug: lowercase, hyphens, descriptive (no version numbers in slug).
- One report per topic per date; append `-v2` only if same-day revision is required.
- Archive old reports to `docs/06-Daily/reports/archive/` when superseded.

---

## ADR Conventions

**Canonical path:** `docs/02-Decisions/adrs/ADR-NNN-slug.md`
Format: three-digit zero-padded number + lowercase-hyphenated slug.
Example: `docs/02-Decisions/adrs/ADR-014-sdd-fast-path.md`

**Canonical location:** `docs/02-Decisions/adrs/` is the only ADR directory. The legacy `docs/04-Concepts/architecture/adrs/` namespace (ADR-087) was removed on 2026-05-12.

When writing a new ADR: copy the structure from the most recent `docs/02-Decisions/adrs/ADR-NNN-*.md` file. Increment NNN sequentially.

---

## What NOT to Read

Skip these unless the task explicitly targets them:

- `docs/99-Archive/archive/` — stale, superseded content
- `docs/06-Daily/reports/archive/` — old reports, kept for audit only
- `docs/SESSION-HANDOFF-*.md` — human hand-off notes, not agent context
- `docs/01-Build-Log/history/` — historical changelog, rarely relevant
- Large generated reports (`adr-200-plus-closure-inventory-*.md`, etc.) unless the task is ADR inventory work
- `docs/08-References/assets/` — images/diagrams only
- `docs/RED-TEAM-*.md` — red-team logs, relevant only for security review tasks
