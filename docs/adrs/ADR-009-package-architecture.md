# ADR-009: Package Architecture -- 375 Agentic Primitives Reclassified

**Date:** 2026-03-28
**Status:** Accepted
**Commits:** 688f669, 677e8af, 83b3d99, b217282, 2c3baee
**Engram IDs:** 1671, 1701, 1704, 1719

## Context

Cognitive OS had grown to 375+ agentic primitives (72+ skills, 55+ rules, 57+ hooks, 40+ libs) all stored flat in their respective directories. There was no clear boundary between what constituted the OS kernel and what was an optional add-on. The `cos` package manager had been built but had no packages from the OS's own codebase to manage. Everything was installed together, regardless of whether a user needed it.

## Decision

Perform a full audit of every agentic primitive and restructure the codebase into CORE (stays in root) and PACKAGE (moves to `packages/` directory):

- **CORE (82 agentic primitives)**: 9 skills, 24 hooks, 38 rules, 8 libs, 3 templates, plus the Go CLI. These are the irreducible OS kernel — agentic primitives every installation needs.
- **PACKAGE (227 agentic primitives)**: 93 skills, 41 hooks, 44 rules, 41 libs, 3 agents, 5 templates. Optional add-ons organized into 23 packages under `packages/`, each with a `cos-package.yaml` manifest.

The migration used `git mv` plus directory symlinks at original locations for backward compatibility. This pattern proved bulletproof -- not a single test needed path updates. All 1723 Python tests and 210+ Go tests passed after migration.


The plugin marketplace (`cos install`, `cos publish`, `cos search`) was designed with two modes of package creation:
- **Generated**: COS reads a repo's structure and auto-generates adapted skills, hooks, and rules.
- **Curated**: Pre-built packages from trusted sources, downloaded as-is with attribution.

Security was built in: every package goes through a license check (block AGPL/SSPL/GPL), secret scanning, prompt injection scanning (via parry), and dependency analysis before installation.

## Alternatives Considered

- **Keep flat structure with tags**: Add metadata tags to agentic primitives instead of moving files. Rejected because it doesn't enable independent versioning, selective installation, or package distribution.
- **Separate repositories per package**: Full independence like npm packages. Rejected as premature -- monorepo with internal packages keeps development velocity high while establishing the package boundary.
- **npm/Cargo-style package manager**: Use an existing package manager ecosystem. Rejected because agentic primitives (skills, hooks, rules) don't fit the file structure assumptions of language-specific package managers. A Brew-style model (formula = metadata, install = copy) was chosen instead.

## Consequences

- Only 22% of agentic primitives are truly CORE; 78% are optional. The OS kernel is much smaller than it appeared.
- The symlink backward compatibility pattern means existing installations continue to work without changes.
- Each package can be independently versioned (semver), documented, and tested.
- The `cos` CLI gained install, remove, list, audit, update, search, and publish commands with a full lifecycle.
- Supply chain hardening was added: commit hash pinning, per-file integrity checks, and SHA256 digest pinning for all Docker images (responding to the TeamPCP attack of March 2026).
