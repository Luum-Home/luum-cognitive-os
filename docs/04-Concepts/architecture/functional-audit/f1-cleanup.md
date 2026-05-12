---
date: 2026-04-16
author: F1 skills audit agent
phase: reconstruction
---

# F1 Skills Audit — Cleanup Decision Record

## T1: Frontmatter Bug — 6 Skills Fixed

YAML `---` block was placed AFTER the `# Title` H1 in 6 skills, making it invisible to strict YAML parsers. Fixed by moving the YAML frontmatter block to the top of each file.

Files fixed:
- `skills/agent-stress-test/SKILL.md`
- `skills/auto-rollback/SKILL.md`
- `skills/capability-snapshot/SKILL.md`
- `skills/cognitive-os-status/SKILL.md`
- `skills/impact-analysis/SKILL.md`
- `skills/red-team/SKILL.md`

## T2: Empty Directory `skills/auto-generated/` Removed

The directory contained only a `.gitkeep` placeholder file (no SKILL.md, no content). Removed the placeholder and the directory. No CATALOG references existed.

## T3: `coverage-enforcement` — Broken Hook Reference Stripped

Decision: **keep the skill, strip the broken reference**.

The skill is referenced in:
- `skills/CATALOG.md`
- `skills/CATALOG-COMPACT.md`
- `docs/architecture.md`, `docs/singularity.md`, `docs/os-vs-project-separation.md`, `docs/component-audit.md`, and others

Removing the skill would orphan these consumers. The `coverage-gate.sh` hook was referenced only in the skill's own Integration section (as an optional integration point) and in `docs/configurable-quality-gates.md` / `docs/complexity-audit.md` (docs only, not functional code).

Action: removed the `coverage-gate.sh` bullet from the Integration section and added the comment `<!-- coverage-gate.sh deferred; hook not yet implemented -->` in its place. The skill itself (the `/coverage-report` command) is fully functional without the hook.

## T4: `arena` — Broken Path Reference Fixed

Decision: **keep the skill, fix the path**.

The skill is referenced in `skills/CATALOG.md` and `skills/CATALOG-COMPACT.md`. The referenced script `run-arena.sh` DOES exist — at `tests/arena/run-arena.sh`. The SKILL.md incorrectly referenced it as `.cognitive-os/tests/arena/run-arena.sh` (a path that does not exist).

Action: updated all path references in `skills/arena/SKILL.md` from `.cognitive-os/tests/arena/` to `tests/arena/`.
