# cos-update.sh vs Go `cos` CLI — Responsibility Analysis

**Date**: 2026-04-24
**Type**: Read-only analysis (no code changes)
**Related**: ADR-066 (polyglot boundaries — in flight)

## Executive Summary

There is **significant functional overlap but distinct operational scopes** between `scripts/cos-update.sh` (bash) and the Go `cos` CLI:

- **`scripts/cos-update.sh`**: An **orchestrator script** that manages the full Cognitive OS update lifecycle: backups, version changes, settings regeneration, Python deps, Docker containers, MCP registration, and verification.
- **Go `cos` CLI**: A **package manager** for individual cos-packages (skills, rules, hooks, agents, templates), with subcommands for install, update, release, publish, and registry management.

The two systems operate at **different layers**: `cos-update.sh` is self-hosting infrastructure; the Go CLI is a general-purpose package manager. However, `cos update` (the CLI subcommand) **does NOT appear to be called from `cos-update.sh` or vice versa**, creating an orphaned CLI command.

## Components Inspected

### scripts/cos-update.sh (774 lines, bash)
**Purpose**: Idempotent full-stack Cognitive OS update with backup, verify, and rollback.

**What it does**:
1. Pre-state snapshot (SHA-256 of settings + dir listings)
2. Backup creation and rotation (keeps last 3 backups)
3. Python deps sync via `uv sync` (if pyproject.toml changed)
4. Settings regeneration via `apply-efficiency-profile.sh` (if profile script changed)
5. Docker container recreation (if docker-compose.yml changed)
6. MCP registration via `scripts/register-mcps.sh`
7. Self-install via `hooks/self-install.sh` (delegates skill/rule symlink updates)
8. Post-state snapshot and diff
9. Verification: re-run self-install, pytest audit, go build
10. Rollback on verify failure (automatic with `--auto-rollback`)

**Flags**: `--dry-run`, `--auto-rollback`, `--no-verify`, `--force`, `--pull-images`, `--help`

**Call sites**: 
- Documented in getting-started.md
- Used in manual tests (lote-2-mcp-loop.md)
- Referenced in release criteria

### Go `cos` CLI (from cmd/cos/internal/cli/)
**Purpose**: Package manager for reusable AI agent components.

**Subcommands** (31 total):
- **Package management**: `init`, `validate`, `install`, `remove`, `update`, `list`, `search`, `info`, `audit`, `publish`, `add`
- **Registry management**: `registry` (list, add, enable, disable)
- **Project setup**: `new`, `setup`
- **System info**: `version`, `status`, `map`, `perf`
- **Release management**: `release`, `release-all`, `changelog`

**Notable subcommand: `cos update`** (cmd/cos/internal/cli/update.go, 217 lines)
- Checks for newer versions of installed packages
- Skips local packages
- For each outdated package: remove old, install new version
- No backup, no verify, no rollback
- Minimal scope: only operates on cos-packages, not OS-wide state

## Responsibility Matrix

| Responsibility | scripts/cos-update.sh | Go `cos update` | Notes |
|---|---|---|---|
| Backup before change | ✓ YES | ✗ NO | Bash creates .cognitive-os/backups/pre-update-*/, Go has no backup |
| Version check | ✗ NO | ✓ YES (via resolver.Fetch) | Bash defers to hooks; Go checks each package separately |
| Update individual packages | ✗ NO (via hooks) | ✓ YES (primary purpose) | Bash delegates to self-install.sh; Go is native |
| Python deps sync (uv) | ✓ YES (conditional) | ✗ NO | Bash monitors pyproject.toml; Go has no dependency sync |
| Settings regeneration | ✓ YES (conditional) | ✗ NO | Bash monitors apply-efficiency-profile.sh; Go has no settings awareness |
| Docker container mgmt | ✓ YES (conditional) | ✗ NO | Bash detects compose file changes; Go has no Docker integration |
| MCP registration | ✓ YES (always) | ✗ NO | Bash calls register-mcps.sh; Go has no MCP awareness |
| Verify installation | ✓ YES (mandatory unless --no-verify) | ✗ NO | Bash runs self-install re-run, pytest, go build; Go has no post-install checks |
| Rollback on failure | ✓ YES (with --auto-rollback or interactive) | ✗ NO | Bash can restore from backup; Go cannot |
| Idempotence check | ✓ YES (short-circuit on no changes) | ✗ NO (always proceeds) | Bash compares pre/post fingerprints; Go updates even if up-to-date |
| Update ALL packages | ✓ YES (implied: self-hosting) | ✓ YES (with `cos update` and no args) | Both support full update |
| Update specific package | ✗ NO | ✓ YES (`cos update <package>`) | Bash is OS-wide only; Go is per-package |

## Call Sites

| Invoker | Invokes | Context |
|---|---|---|
| User docs (getting-started.md) | `bash scripts/cos-update.sh` | Initial setup and regular updates |
| User docs (getting-started.md) | `bash scripts/cos-update.sh --pull-images` | Also update Docker images |
| Manual tests (lote-2-mcp-loop.md) | `bash scripts/cos-update.sh --no-verify` | Test MCP integration |
| Release docs | `scripts/cos-update.sh --auto-rollback` | Safe update with auto-rollback |
| (None found) | `cos update` (Go CLI) | Package manager is unused in bash scripts/docs |

**Key finding**: The Go `cos update` subcommand has **no call sites** in the codebase. It is not invoked from any bash script, hook, or documented procedure. The bash `scripts/cos-update.sh` is the only active update mechanism.

## Overlap Assessment

### True Overlap
- **Package version updates**: Both bash (via hooks/self-install.sh) and Go (native) can update cos-packages. However, they operate independently.
- **Full vs. selective updates**: Both support updating all or specific packages, but via different UX (bash: all, Go: per-package).

### Apparent Overlap but Actually Different
- **`cos update` command naming**: The Go CLI's `cos update [package]` is a package-specific updater; `scripts/cos-update.sh` is a full-stack OS updater. The names suggest the same responsibility, but they operate at different layers.

### Gaps (Neither Does This)
- **Incremental package updates**: No mechanism to update only changed packages (Go's `cos update` requires manual selection or "update all").
- **Cross-package dependency resolution**: `cos update` uses MVS but does not propagate transitive updates across the OS.
- **Integration with external registries**: `scripts/cos-update.sh` does not query remote registries; it only re-runs self-install.

## Recommendation

### Pick: **A) Keep Split, Clarify Boundaries**

**Justification**:
1. **Different operational scopes**: `scripts/cos-update.sh` is a **self-hosting infrastructure script** (updates the Cognitive OS project itself). The Go CLI is a **general-purpose package manager** (for downstream projects using COS). These should coexist.

2. **Non-overlapping call paths**: `cos-update.sh` is invoked by users and docs; `cos update` (Go) is orphaned. There is no conflict, only documentation and discoverability gaps.

3. **Self-hosting vs. distributed**: The bash script updates .cognitive-os/ in place with Python deps, Docker, MCP registration. The Go CLI installs packages into `cos/@org/pkg/` namespaces for reuse. These are genuinely different use cases.

4. **Cost of consolidation**: Merging would require:
   - Moving Python/Docker/MCP orchestration into Go (significant work)
   - Abandoning the bash script's idempotence + backup + verify + rollback pattern
   - Breaking downstream projects that may already depend on the CLI

5. **Keeping split is lower-risk**: Document the boundary clearly; ensure `cos update` either (a) works for end-users or (b) is removed if it's not a supported command.

## Migration Cost (if consolidation were chosen)

**Consolidation option B (into Go)**: HIGH COST
- Implement Python dep sync in Go: ~500 LOC Go + cgo bindings for uv
- Implement Docker integration: ~400 LOC Go
- Implement MCP orchestration: ~300 LOC Go
- Implement idempotence + backup + verify: ~600 LOC Go
- Remove `scripts/cos-update.sh`: -28K LOC bash (deletion only)
- **Total**: +1.8K LOC Go, test coverage required, distribution changes (Go binary size increase)

**Consolidation option C (into bash)**: NOT RECOMMENDED
- Go CLI has valid use cases (package discovery, registry management, structured JSON output)
- Would require removing the Go binary as a distributed artifact
- Loses type safety and performance benefits of Go

**Chosen approach (A: Clarify boundaries)**: LOW COST
- Update ADR-066 to document split (orchestrator vs. package manager)
- Add disambiguation to `cos update` help text
- Add a note in cognitive-os.yaml: "For full-stack OS updates, use `bash scripts/cos-update.sh`. For individual package updates, use `cos update <pkg>`."
- Cost: ~2 hours documentation, 0 LOC changes

## Open Questions

1. **Is `cos update` (Go CLI) actively used by downstream projects?** If so, it is valid as a reusable package manager. If not, consider deprecating or marking as internal.

2. **Should `scripts/cos-update.sh` eventually call `cos update` to unify logic?** Possible future refactor: have `cos-update.sh` delegate to Go binary for the update step (after Python/Docker/MCP setup). This requires the Go CLI to gain idempotence + verify + rollback capabilities.

3. **What does ADR-066 say about polyglot boundaries?** If ADR-066 establishes a clear rule for Go vs. bash, apply it here. (Assumption: Go for general-purpose tools, bash for OS-specific infrastructure.)

4. **Is the `scripts/cos` wrapper still relevant?** It routes `cos status` to bash and other commands to an old CLI. Clarify if the Go CLI should replace it entirely.

## References

- `scripts/cos-update.sh`: 774 lines, orchestrator script with idempotence + backup + verify + rollback
- `cmd/cos/internal/cli/update.go`: 217 lines, package-level updater
- `cmd/cos/README.md`: Command reference and usage examples
- `cmd/cos/internal/cli/root.go`: CLI command structure (31 total subcommands)
