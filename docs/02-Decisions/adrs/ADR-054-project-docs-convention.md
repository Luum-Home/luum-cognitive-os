---
adr: 54
title: Project Documentation Convention (10 Categories)
status: accepted
implementation_status: partial
date: '2026-04-21'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: — Deferred; convention over enforcement for v1.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-054 — Project Documentation Convention (10 Categories)

## Status

**Accepted** — 2026-04-21. Implementation lives in `lib/project_scaffolder.py`
+ `scripts/project_scaffold.py` + `skills/project-scaffold/`. Behavior
tested via 19 real-filesystem tests.

## Context

Projects that adopt Cognitive OS have been organizing their `docs/`
directory ad-hoc. Each project picked its own folder names (`design/`,
`specs/`, `architecture/`, etc.), making SO skills that emit
documentation (`document-feature`, `security-audit`, `deep-research`,
`sdd-tasks`) unable to write to a predictable location.

Audit (2026-04-21) found that adopting projects already converged on a
**10-category convention** in practice:

| # | Dir | Purpose |
|---|---|---|
| 01 | `01-context` | Business context, stakeholders, problem framing |
| 02 | `02-architecture` | System design, components, diagrams |
| 03 | `03-domain-risk` | Domain model + risk register (combined by design) |
| 04 | `04-security` | Threat model, controls, incident response |
| 05 | `05-features` | Feature inventory and backlog |
| 06 | `06-backoffice` | Operations, admin processes, monitoring |
| 07 | `07-research` | Research spikes, competitive analysis |
| 08 | `08-standards` | Coding, doc, review standards |
| 09 | `09-execution-plan` | Roadmap, sprints, estimation |
| 10 | `10-summaries` | Executive summaries, status reports |

The SO had skills covering ~60% of these categories but (a) no single
skill scaffolded the whole tree, and (b) several skills emitted output
to locations that didn't match the convention.

## Decision

**Formalize the 10-category convention as a Cognitive OS standard** for
adopting projects. Ship tooling to:

1. Scaffold the whole tree in one call (`/project-scaffold`).
2. Keep the dir names and numbering fixed (the numeric prefix drives
   natural sort + enforces canonical order).
3. Cross-reference SO skills in each category's README so users know
   which tool feeds which directory.

### Invariants

- The category **count (10) and names are part of the contract**. Changing
  them breaks downstream skills that emit into these dirs. Changes
  require a new ADR.
- Spanish dir names are intentional (the convention originated in a
  Spanish-speaking team). File names inside are English by default.
- Combination `03-domain-risk` is deliberate — domain modeling and
  risk assessment co-evolve; separating them leads to both being ignored.

### Skill mapping (authoritative)

| Category | SO skill(s) that feed it |
|---|---|
| 01-context | `deep-research`, `scout-pattern` |
| 02-architecture | `sdd-design`, `sdd-spec` |
| 03-domain-risk | `sdd-propose` (domain part); risk is human-curated |
| 04-security | `security-audit`, `pentest-self`, `red-team` |
| 05-features | `document-feature`, `sdd-propose` |
| 06-backoffice | — (primarily human-curated; ops runbooks) |
| 07-research | `deep-research`, `repo-scout`, `repo-forensics` |
| 08-standards | mirrors `rules/*.md` — can be generated |
| 09-execution-plan | `sdd-tasks`, `exhaustive-prompt`, `cos-sprint` |
| 10-summaries | `session-wrapup`, `compress`, `generate-changelog` |

## Consequences

### Positive

- Adopting projects get a consistent shape — onboarding cost drops.
- SO skills can safely assume `docs/<NN-category>/` exists when asked to
  write documentation.
- The scaffolder is idempotent, so existing projects can run it without
  clobbering work-in-progress files.
- Tests (19 real-filesystem, zero mocks) prevent drift.

### Negative

- Dir names are hardcoded in Spanish — mixed-language teams must accept
  that. Aliasing is out of scope for v1.
- `06-backoffice` and `03-domain-risk` have no dedicated skill today.
  They're scaffolded with TODO markers but require human work. Future
  work: skills to generate starter content from domain prompts.

### Neutral

- The convention is declared but not enforced on adopting projects. A
  project may keep any extra directories; the scaffolder only creates
  the 10 canonical ones.

## Verification

- `uv run pytest tests/unit/test_project_scaffolder.py -v` — 19/19 pass.
- Manual smoke: `uv run python3 scripts/project_scaffold.py --project-dir /tmp/xyz --project-name Demo --json` — should create 34 files across 10 dirs.
- Every category's README references at least one SO skill or points to
  a human-curated section.

## Related

- `lib/project_scaffolder.py` — single source of truth for categories.
- `skills/project-scaffold/SKILL.md` — user-invocable entry point.
- `scripts/project_scaffold.py` — CLI.
- Engram: `gap/project-doc-scaffolding-skills` — the gap audit that
  motivated this ADR.
- ADR-027 — SO slimming (keeps scaffolder lean, no LLM calls in v1).

## Open questions

1. Should adoption be enforced via a rule (fail CI if dirs are missing)?
   — Deferred; convention over enforcement for v1.
2. Should `03-domain-risk` split into 03a-domain + 03b-risk later?
   — Empirically the two co-evolve; keep combined.
3. Should there be a `/project-scaffold-migrate` variant that renames
   existing ad-hoc dirs to the convention? — Future, scoped out of v1.
