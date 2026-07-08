---
type: concept-synthesis
source: docs/04-Concepts/architecture/cos-update-vs-cos-cli-responsibility-analysis.md
status: "Read-only analysis, no code changes"
provenance: "Investigates whether scripts/cos-update.sh (bash) and the Go cos CLI's update subcommand overlap or conflict, in the context of ADR-066 polyglot boundaries."
---

## What it is
Responsibility analysis (2026-04-24) comparing `scripts/cos-update.sh` (bash, full-stack OS self-update orchestrator) against the Go `cos` CLI's `update` subcommand (per-package manager), concluding they serve different layers and should stay split.

## Key mechanics
- `scripts/cos-update.sh` (774 lines): pre-state SHA-256 snapshot, backup + rotation (last 3), Python deps sync via `uv sync` (conditional on pyproject.toml change), settings regen via `apply-efficiency-profile.sh`, Docker container recreation, MCP registration via `register-mcps.sh`, self-install via `hooks/self-install.sh`, post-state diff, verification (self-install re-run, pytest audit, go build), automatic rollback on verify failure (`--auto-rollback`). Flags: `--dry-run`, `--auto-rollback`, `--no-verify`, `--force`, `--pull-images`, `--help`.
- Go `cos update` (`cmd/cos/internal/cli/update.go`, 217 lines): checks for newer versions of installed cos-packages, skips local packages, removes+reinstalls outdated ones; no backup, no verify, no rollback; operates only on packages, not OS-wide state. `cos` CLI has 31 subcommands total (package mgmt, registry, project setup, system info, release mgmt).
- Responsibility matrix: bash has backup/idempotence/verify/rollback/Python-deps/settings/Docker/MCP that Go lacks; Go has native version-check and per-package update that bash lacks (bash delegates package updates to hooks/self-install.sh).
- Key finding: Go `cos update` has zero call sites in the codebase (not invoked from any script, hook, or documented procedure) - it is orphaned. `scripts/cos-update.sh` is the only actively used update mechanism (referenced in getting-started.md, lote-2-mcp-loop.md, release docs).
- Recommendation: Option A, keep split and clarify boundaries (low cost, ~2 hours documentation, 0 LOC). Rejected: Option B consolidate into Go (~1.8K LOC Go, removes 28K LOC bash) and Option C consolidate into bash (loses Go's type safety/registry/JSON output).
- Open questions: is `cos update` used downstream; should `cos-update.sh` eventually delegate to the Go binary; what exactly does ADR-066 mandate; is the `scripts/cos` wrapper (routes `cos status` to bash, rest to an old CLI) still relevant.

## Relations & where used
ADR-066 (polyglot boundaries, in flight). Files: `scripts/cos-update.sh`, `cmd/cos/internal/cli/update.go`, `cmd/cos/README.md`, `cmd/cos/internal/cli/root.go`.

## Status / caveats
Read-only analysis, no code changes made. Recommendation (clarify boundaries in ADR-066 plus help text plus cognitive-os.yaml note) not confirmed as executed within this doc.
