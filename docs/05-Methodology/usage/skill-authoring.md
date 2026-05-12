---
title: Skill Authoring Guide
audience: os-dev
---

# Skill Authoring Guide

This document defines the contract for authoring SKILL.md files in `skills/*/`. Every skill
must pass the contract tests in `tests/audit/test_skills_contracts.py` before merging.

## Required Structure

Every `skills/{name}/SKILL.md` must:

1. Start at line 1 with a YAML frontmatter block (`---` ... `---`).
2. Include at minimum the `name:` key.
3. Close the frontmatter block with `---` before any Markdown heading.
4. Be listed in `skills/CATALOG.md` or `skills/CATALOG-COMPACT.md`.

## Frontmatter Fields

### Required

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique skill identifier, matches the directory name. No spaces. |

### Recommended

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | One-line summary of what the skill does. Shown in catalog and routing. |
| `version` | string | Semantic version (`1.0.0`). Increment when the protocol changes. |
| `triggers` | list or string | When the skill auto-activates. Values: `manual`, `pattern`, `auto`. |
| `audience` | string | Who invokes it: `os-dev`, `project`, or `both`. |

### Optional (commonly used)

| Field | Type | Description |
|-------|------|-------------|
| `invoke` | string | Slash command to call this skill (e.g. `/coverage-report`). |
| `effort` | string | Recommended model tier: `haiku`, `sonnet`, or `opus`. |
| `tech` | string | Language or stack filter (e.g. `go`, `ts`). |
| `paths` | list | File glob patterns that trigger the skill when changed. |
| `args` | list | Named arguments the skill accepts. |
| `last-updated` | string | ISO date of last substantive change (`2026-04-13`). |

The YAML block must be valid. All values must be properly quoted if they contain colons or
special characters.

## Minimal Example

```markdown
---
name: my-skill
description: What this skill does in one sentence.
---

# My Skill

## Purpose

...
```

## Complete Example

```markdown
---
name: coverage-enforcement
version: 1.0.0
invoke: /coverage-report
description: Run Go test coverage, enforce thresholds, report per-package results.
audience: project
effort: haiku
tech: go
paths: ["*.go", "go.mod"]
triggers:
  - manual
---

# Coverage Enforcement Skill

## Purpose

...
```

## Reference Hygiene

All internal project paths cited in prose (outside fenced code blocks) must resolve on disk.
The audit test checks paths matching `hooks/`, `scripts/`, `lib/`, `templates/`, `rules/`, and
`packages/` prefixes, plus bare hyphenated `.sh`/`.py` filenames in backticks.

Rules:
- Use full relative paths (`tests/arena/run-arena.sh`) instead of bare filenames
  (`run-arena.sh`) when the file lives outside `hooks/`, `scripts/`, `lib/`, or `packages/`.
- Do not reference files your skill GENERATES in a target project as if they exist in this
  repo. If your skill is a generator (like `scaffold-project`), add it to `_OUTPUT_PATH_SKILLS`
  in `tests/audit/test_skills_contracts.py`.

## Prohibited Markers

SKILL.md must not contain procedural-placeholder language outside fenced code blocks or
quoted strings. The audit test flags:

- `TODO: implement` / `TODO: finish` / `TODO: complete`
- `not yet implemented`
- `aspirational`
- `FIXME:` / `XXX:`
- `placeholder procedure/implementation/logic/section`
- `stub implementation`
- `coming soon`
- `WIP` at line start

If a hook or integration is absent, describe its absence factually:
```
<!-- coverage-gate.sh absent; hook pending (see ADR) -->
```
not:
```
<!-- coverage-gate.sh deferred; hook not yet implemented -->
```

## Linting

Run the full audit suite to validate all skills:

```bash
python3 -m pytest tests/audit/test_skills_contracts.py -m audit -v
```

Run a single skill check:

```bash
python3 -m pytest tests/audit/test_skills_contracts.py -m audit -k my-skill -v
```

The four contracts checked:

| Test | What it verifies |
|------|-----------------|
| `test_every_skill_has_valid_frontmatter` | Frontmatter at line 1, `name:` present |
| `test_every_skill_reference_exists` | All internal path refs resolve on disk |
| `test_every_skill_in_catalog` | Skill listed in CATALOG.md or CATALOG-COMPACT.md |
| `test_no_skill_has_todo_markers` | No procedural-placeholder language |

As of 2026-04-16, all 123 skills pass these contracts.
