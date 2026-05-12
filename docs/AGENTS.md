# AGENTS.md — AI-Agent Routing Guide

Human-curated. <150 lines. Do not auto-generate or overwrite.

---

## Task-to-Doc Routing Table

| Task type         | Read first                        | Then (if needed)                        |
|-------------------|-----------------------------------|-----------------------------------------|
| Bug fix           | `docs/adrs/` (relevant ADR)       | `docs/reports/` (incident/forensics)    |
| New feature       | `docs/architecture-principles.md` | `docs/adrs/`, `docs/skills/`            |
| ADR write         | `docs/adrs/ADR-NNN-slug.md` (latest example) | `docs/architecture.md`         |
| Performance work  | `docs/performance.md`             | `docs/reports/` (benchmarks), `docs/benchmarks/` |
| Security review   | `docs/security-stack.md`          | `docs/compliance/`, `docs/security/`   |
| Release           | `docs/release/`                   | `docs/versioning-strategy.md`           |
| Testing / QA      | `docs/testing.md`                 | `docs/quality/`, `docs/manual-tests/`  |
| Skill authoring   | `docs/skills/`                    | `rules/RULES-COMPACT.md` §11           |
| Hook authoring    | `docs/hooks.md`                   | `rules/RULES-COMPACT.md` §10           |
| Research / report | `docs/reports/` (newest relevant) | `templates/agent-research-only.md`     |

---

## Canonical Terms Glossary

| Term            | Definition                                                                 |
|-----------------|----------------------------------------------------------------------------|
| **COS**         | Cognitive Operating System — this repo; the AI-agent orchestration layer   |
| **ADR**         | Architecture Decision Record; lives at `docs/adrs/ADR-NNN-slug.md`        |
| **primitive**   | Atomic capability unit (a single skill step or tool wrapper)               |
| **harness**     | The IDE/CLI shell hosting the agent (Claude Code, Cursor, Aider, etc.)     |
| **SDD**         | Spec-Driven Development; the repo's change workflow (explore→propose→apply→verify→archive) |
| **skill**       | A named, versioned prompt file that extends agent capabilities             |
| **engram**      | Persistent memory backend used across sessions via `mem_save`/`mem_search` |
| **hook**        | Shell script triggered by harness events (pre-commit, post-task, etc.)     |
| **phase**       | Project maturity mode: reconstruction / production (affects governance)    |
| **DAG**         | Directed Acyclic Graph; SDD dependency graph between phases                |
| **DoD**         | Definition of Done; 5-level quality checklist (`docs/definition-of-done.md`) |
| **blast radius**| Estimated scope of a change (files touched, services affected)             |
| **tombstone**   | An ADR marked superseded/withdrawn; file kept for history                  |
| **lane**        | Test isolation group; registry at `.cognitive-os/test-lanes.yaml`          |
| **cosd**        | COS daemon; remote API requiring `--allow-remote` + bearer auth            |

---

## Report Naming Convention

```
docs/reports/<topic>-YYYY-MM-DD.md
```

Examples: `docs/reports/aspirational-audit-2026-05-08.md`, `docs/reports/ai-agent-harness-landscape-2026-05-04.md`

- Topic slug: lowercase, hyphens, descriptive (no version numbers in slug).
- One report per topic per date; append `-v2` only if same-day revision is required.
- Archive old reports to `docs/reports/archive/` when superseded.

---

## ADR Conventions

**Canonical path:** `docs/adrs/ADR-NNN-slug.md`  
Format: three-digit zero-padded number + lowercase-hyphenated slug.  
Example: `docs/adrs/ADR-014-sdd-fast-path.md`

**Known inconsistency:** `docs/architecture/adrs/` contains a duplicate partial set (files without the `ADR-` prefix, e.g. `006-agpl-license-compliance.md`). Treat `docs/adrs/` as authoritative. Do not create new ADRs in `docs/architecture/adrs/`.

When writing a new ADR: copy the structure from the most recent `docs/adrs/ADR-NNN-*.md` file. Increment NNN sequentially.

---

## What NOT to Read

Skip these unless the task explicitly targets them:

- `docs/archive/` and `docs/archived/` — stale, superseded content
- `docs/reports/archive/` — old reports, kept for audit only
- `docs/SESSION-HANDOFF-*.md` — human hand-off notes, not agent context
- `docs/history/` — historical changelog, rarely relevant
- Large generated reports (`adr-200-plus-closure-inventory-*.md`, etc.) unless the task is ADR inventory work
- `docs/assets/` — images/diagrams only
- `docs/RED-TEAM-*.md` — red-team logs, relevant only for security review tasks
