---
type: methodology-synthesis
source: docs/05-Methodology/usage/skill-authoring.md
provenance: "Defines the mandatory contract for authoring SKILL.md files, enforced by an automated audit test suite, so every skill has valid frontmatter, resolvable references, catalog registration, and no procedural-placeholder language before it can merge."
---

## What it is

The authoring contract for `skills/{name}/SKILL.md` files, enforced by `tests/audit/test_skills_contracts.py`, covering required structure, frontmatter fields, reference hygiene, and prohibited placeholder markers.

## Key mechanics

- Required structure: frontmatter YAML block starting at line 1, at minimum a `name:` key, frontmatter closed with `---` before any Markdown heading, and the skill listed in `skills/CATALOG.md` or `skills/CATALOG-COMPACT.md`.
- Frontmatter fields: only `name` (string, matches directory name, no spaces) is required. Recommended fields are `description`, `version` (semver), `triggers` (`manual`/`pattern`/`auto`), `audience` (`os-dev`/`project`/`both`). Commonly-used optional fields: `invoke` (slash command), `effort` (model tier `haiku`/`sonnet`/`opus`), `tech` (language/stack filter), `paths` (glob triggers), `args`, `last-updated`. Values containing colons or special characters must be quoted.
- Provides a minimal example (just `name` + `description`) and a complete example (`coverage-enforcement` skill showing all recommended/optional fields together).
- Reference hygiene: all internal project paths cited in prose (outside fenced code blocks) matching `hooks/`, `scripts/`, `lib/`, `templates/`, `rules/`, `packages/` prefixes — plus bare hyphenated `.sh`/`.py` filenames in backticks — must resolve on disk. Full relative paths are required for files outside `hooks/`/`scripts/`/`lib/`/`packages/`. Generator skills (like `scaffold-project`) that reference files they *produce* in a target project must be added to `_OUTPUT_PATH_SKILLS` in the audit test to avoid false failures.
- Prohibited markers (outside fenced code blocks/quoted strings): `TODO: implement/finish/complete`, `not yet implemented`, `aspirational`, `FIXME:`, `XXX:`, `placeholder procedure/implementation/logic/section`, `stub implementation`, `coming soon`, leading-line `WIP`. If a hook/integration is genuinely absent, the doc must describe it factually (e.g. `<!-- coverage-gate.sh absent; hook pending (see ADR) -->`) rather than with deferred/placeholder language.
- Linting: full suite via `python3 -m pytest tests/audit/test_skills_contracts.py -m audit -v`; single-skill check via `-k my-skill`. Four named contracts: `test_every_skill_has_valid_frontmatter`, `test_every_skill_reference_exists`, `test_every_skill_in_catalog`, `test_no_skill_has_todo_markers`.
- States that as of 2026-04-16, all 123 skills pass these contracts.

## Relations & where used

Directly enforced by `tests/audit/test_skills_contracts.py`; references `skills/CATALOG.md` and `skills/CATALOG-COMPACT.md` as the registration surfaces every skill must appear in.

## Status / caveats

The "as of 2026-04-16, all 123 skills pass" claim is a dated point-in-time snapshot — the skill count and pass state will drift as skills are added/modified after that date; treat the contract rules themselves (frontmatter, reference hygiene, placeholder markers) as the durable content and the pass-count as historical evidence only.
