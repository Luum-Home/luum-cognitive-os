# Archived Packages

This directory is **not a package** — it is a holding area for components that
have been retired from active use but preserved for historical reference and git
history.

## Contents

| Path | What it holds | Archived when |
|------|---------------|---------------|
| `squads/` | 4 squad YAML templates (infra, mobile, payments, platform) | Sprint 2A, 2026-04-16 |

## Why `packages/_archived/` and not `_archived/`?

Placement under `packages/` keeps the `cos-index` scanner and `self-install.sh`
pathing uniform. The leading underscore is the widely-used convention for
"not a real package — skip".

Tools that iterate `packages/*`:

- `tests/audit/test_integrity.py::test_every_package_has_readme_or_skill_md`
  accepts this README as evidence of documentation (satisfied).
- `tests/audit/test_integrity.py::test_counts_match_expected_shape` requires
  `len(packages) >= 1`; adding `_archived/` does not reduce the count.
- `hooks/self-install.sh` iterates packages by manifest presence
  (`cos-package.yaml`) — this dir has no manifest, so it is silently skipped.

## Un-archiving

To un-archive a component, `git mv` its subdirectory back to its canonical
location and restore any broken cross-references. See the contents'
subdirectory READMEs for per-component un-archive checklists.
