# Maps of Content (MOCs)

MOCs are **curated entrypoints** to the docs tree. They are short, link-heavy index pages — *not* content. The actual material lives in the real subdirectories (`docs/02-Decisions/adrs/`, `docs/04-Concepts/architecture/`, etc.); MOCs only tell you which to read first.

## When to read a MOC vs. `docs/00-MOCs/entrypoints/INDEX.md`

- **`docs/00-MOCs/entrypoints/INDEX.md`** is the exhaustive flat catalogue — every subdir, every loose file. Use when you need to find something by name.
- **MOCs here** are thematic doorways for a specific intent ("I want to make a decision", "I'm onboarding", "I need to ship a release"). Use when you don't yet know what to read.

## Available MOCs

| MOC | Read when… |
|---|---|
| [decisions.md](decisions.md) | You're about to write or supersede an ADR, or need to understand a past decision. |
| [architecture.md](architecture.md) | You're designing a new component or trying to understand how parts fit together. |
| [workflow.md](workflow.md) | You're running a multi-step process — sprints, SDD, self-improvement, runbooks. |
| [quality.md](quality.md) | You're writing tests, doing security review, or auditing for compliance. |
| [operations.md](operations.md) | You're running the system day-to-day — incidents, releases, capabilities, ops reference. |
| [onboarding.md](onboarding.md) | You (or an agent) are new to this project and need orientation. |

## Maintenance rule

A MOC line must point at a real file or directory. Run a broken-link check after any subdir rename. MOCs are **human-curated** — do not auto-generate (auto-generation reduces task success per the 2026 ETH study; see `docs/06-Daily/reports/docs-organization-research-2026-05-12.md`).

Last updated: 2026-05-12
