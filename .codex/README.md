# Codex Workspace Layer

This directory contains compressed, Codex-specific working context for the
repository.

It exists to reduce repeated repository exploration while keeping the source of
truth in the real code and documentation.

## Contents

- `config.toml` — local Codex workspace behavior
- `hooks.json` — Codex-facing hook projection starter
- `project-index.md` — compact project and product orientation
- `fast-paths.md` — high-signal commands and validation shortcuts
- `skills/repo-map/` — quick repo navigation
- `skills/test-matrix/` — targeted test selection
- `skills/portability-work/` — cross-harness change discipline
- `skills/docs-to-artifact/` — turn important analysis into durable repo artifacts

## Rules

- Keep this directory compact and stable.
- Do not duplicate volatile implementation details from the repo.
- Prefer maps, checklists, and decision summaries over code snapshots.
- When the project understanding changes, update these files with the smallest
  possible diff.
