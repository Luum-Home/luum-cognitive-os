<!-- SCOPE: project -->
---
name: project-scaffold
description: >
  Scaffold the 10-category docs/ tree adopted by Cognitive OS projects.
  Creates 01-contexto through 10-resumenes with starter files and TODO
  markers. Idempotent. See ADR-054.
version: 1.0.0
user-invocable: true
disable-model-invocation: false
auto-generated: false
last-updated: 2026-04-21
license: MIT
metadata:
  author: luum
audience: project
summary_line: "Create the 10-category docs/ convention (ADR-054) in a project root."
triggers:
  - scaffold project
  - scaffold docs
  - new project
  - project structure
  - 10 categories
platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\bproject[- ]?scaffold\b'
    confidence: 0.95
  - pattern: '\bscaffold\s+project\b'
    confidence: 0.85
---

## Purpose

Adopting projects organize their documentation in 10 canonical
categories (ADR-054). This skill creates the whole tree in one call
instead of each project reinventing its own structure.

Categories:

| # | Dir | Covers |
|---|---|---|
| 01 | `01-contexto` | Business context, stakeholders |
| 02 | `02-arquitectura` | System design, components, decisions |
| 03 | `03-dominio-riesgo` | Domain model + risk register |
| 04 | `04-seguridad` | Threat model, controls, IR |
| 05 | `05-features` | Feature inventory |
| 06 | `06-backoffice` | Ops runbooks, admin, monitoring |
| 07 | `07-investigacion` | Research spikes, competitive analysis |
| 08 | `08-estandares` | Coding / doc / review standards |
| 09 | `09-plan-ejecucion` | Roadmap, sprints, estimation |
| 10 | `10-resumenes` | Exec summaries, status reports |

## Invocation

```bash
uv run python3 scripts/project_scaffold.py \
    --project-dir /path/to/project \
    --project-name "My Project" \
    [--overwrite] [--json]
```

## Behaviour contract

- **Idempotent**: re-running leaves existing files alone unless `--overwrite`.
- **34 files total**: 1 top-level `docs/README.md` + 33 starter files.
- **Every category has a README.md** listing its files + purpose.
- **No network, no LLM** — pure filesystem scaffolding.
- **Cross-refs embedded**: each category's README mentions the SO skill that
  feeds it (e.g. `04-seguridad/README.md` references `security-audit`).

## When to invoke

- Starting a new project that will adopt Cognitive OS conventions.
- Migrating an existing project that has ad-hoc docs/ — run with
  `--no-overwrite` (default) to fill gaps without touching current content.

## Related

- `lib/project_scaffolder.py` — implementation
- `scripts/project_scaffold.py` — CLI
- `docs/adrs/ADR-054-project-docs-convention.md` — convention standard
- `tests/unit/test_project_scaffolder.py` — 19 behavior tests

## Verification

Run: `uv run pytest tests/unit/test_project_scaffolder.py -v`.
Every category is covered by at least one test; idempotency + overwrite
semantics are exercised with real filesystem (no mocks).

## Contextual Trigger

Active when a user asks to "create docs structure", "scaffold a new
project", "apply the 10-category convention", or similar.
