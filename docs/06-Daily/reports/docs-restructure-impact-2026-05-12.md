# Docs Restructure Impact Analysis — 2026-05-12

Companion to `docs-organization-research-2026-05-12.md`. Quantifies code-side breakage if `docs/` is renamed to a vault-numbered scheme (`00-MOCs/`, `01-Build-Log/`, `02-Decisions/`, …).

## Headline Risk Number

**197 code files break** on a naive big-bang rename, plus **151 symlinks** in `.cognitive-os/docs/`.

| Category | Files with `docs/` refs |
|---|---|
| Python tests (`tests/`) | 111 |
| Shell hooks (`hooks/`) | 27 |
| Shell scripts (`scripts/`) | 22 |
| Rules (`rules/*.md`) | 25 |
| Go source (`cmd/`, `internal/`) | 12 |

No CI/CD workflow files reference `docs/` paths. No config YAML/TOML/JSON files reference `docs/` paths (excluding `node_modules` and `package-lock.json`).

## Top 10 Most-Referenced Subpaths

Ranked by aggregate mention count across all non-docs source files:

| Rank | Subpath | Approx. mentions | Files |
|---|---|---|---|
| 1 | `docs/adrs/` | ~80 | 30+ |
| 2 | `docs/reports/` | ~65 | 25+ |
| 3 | `docs/INDEX.md` | ~13 | 5 |
| 4 | `docs/research/` | ~10 | 6 |
| 5 | `docs/capabilities/` | ~8 | 4 |
| 6 | `docs/history/` | ~6 | 4 |
| 7 | `docs/runbooks/` | ~5 | 4 |
| 8 | `docs/manual-tests/` | ~4 | 3 |
| 9 | `docs/architecture/adrs/` | ~4 | 3 |
| 10 | `docs/acc/` | ~2 | 2 |

ADRs currently exist at **two locations** — `docs/adrs/` (282 files, primary) and `docs/architecture/adrs/` (26 files, stubs from ADR-087 migration). The hook `adr-detector.sh` checks `docs/architecture/adrs/`, while all other callers use `docs/adrs/`.

## Top 5 Most Fragile Callers

1. **`hooks/session-startup-protocol.sh:87`** — Hardcodes `ADRS_DIR="$PROJECT_DIR/docs/adrs"` and scans it on every session start. String literal. Breaks immediately on rename. Fires on every Claude Code startup.

2. **`lib/self_improvement_loop.py`** — Hardcodes `"docs/adrs/"`, `"docs/reports/"`, `"docs/manual-tests/"` as literal path strings fed to agent sub-tasks. Called from the self-improvement loop. Any rename silently misdirects agent writes to nonexistent paths.

3. **`cmd/cos/internal/cli/release.go:350`** — Hardcodes `filepath.Join(projectRoot, "docs", "INDEX.md")` and `git add docs/INDEX.md`. If `docs/INDEX.md` moves, every `cos release` invocation silently skips the version bump and fails the git-add.

4. **`hooks/research-quality-validator.sh:36-38` + `hooks/skill-post-execution-analysis.sh:29`** — Both use `docs/reports/` as a hard-coded target directory. The quality validator runs on every pre-commit for files matching `*docs/reports/*.md` — if that glob no longer matches, all research output bypasses quality gating entirely.

5. **`lib/adr_detector.py:68`** — The regex `r"^docs/(?:architecture/)?adrs/"` is the canonical ADR path recognizer used by the `cos` CLI, ADR router, tombstone, reserve-slot, and test suite (11 unit tests). Renaming `docs/adrs/` to `02-Decisions/` breaks this regex and all downstream ADR tooling simultaneously.

## ADR Numbering Convention

ADRs follow `ADR-NNN-slug.md` (zero-padded 3-digit) in `docs/adrs/`. The proposed `02-Decisions/` directory name does not encode ADR numbers in the directory name, so numbering is preserved **within** files. However: `lib/adr_detector.py`'s regex, `hooks/session-startup-protocol.sh`'s `ADRS_DIR`, `hooks/adr-detector.sh` (which uses the divergent `docs/architecture/adrs/` path), and 11 test files all assert the `docs/adrs/ADR-NNN-*.md` path pattern as a string literal. Any rename invalidates those assertions.

## Symlink Risk (CRITICAL)

The `.cognitive-os/docs/` directory contains **151 symlinks** pointing into `docs/` — including directory-level symlinks for `docs/adrs`, `docs/reports`, `docs/runbooks`, `docs/skills`, `docs/archive`, `docs/archived`, `docs/architecture`, `docs/research`, `docs/capabilities`, `docs/security`, `docs/patterns`, and many individual files. These are used by the cognitive OS runtime to access docs at predictable paths. Moving any of these directories breaks all 151 symlinks simultaneously. The symlink `docs/patterns/ecosystem-tools.md` also points outward to `packages/ecosystem-tools/rules/`.

## In-Progress Git Renames

At time of audit: no `git mv` in progress. Only 4 untracked new files in `docs/reports/` (pending checkboxes and analysis reports, all dated 2026-05-12).

## Recommended Migration Strategy: Symlink-Bridge (Gradual)

A big-bang rename is high-risk: 197 code files + 151 `.cognitive-os` symlinks all break simultaneously, with many hooks firing on every session or commit.

Recommended approach:

1. **Phase 1 — Create new structure alongside old.** Create `02-Decisions/`, `04-Concepts/`, etc. as new directories. Do not delete old paths yet.
2. **Phase 2 — Symlink bridges.** Create `docs/adrs` → `02-Decisions/`, `docs/reports` → `01-Build-Log/reports`, etc. as directory symlinks so all 197 callers and 151 `.cognitive-os` symlinks continue to resolve. Update `.cognitive-os/docs/` symlinks to point to the new canonical paths.
3. **Phase 3 — Code surgery.** Update `lib/adr_detector.py` regex, `hooks/session-startup-protocol.sh` `ADRS_DIR`, `cmd/cos/internal/cli/release.go` `INDEX.md` path, `lib/self_improvement_loop.py` path literals, `hooks/research-quality-validator.sh` and `hooks/skill-post-execution-analysis.sh` path constants, and the 111 Python test files (most use `tmp_path / "docs/adrs/..."` which are fixture paths — those are safer but still document the expected schema).
4. **Phase 4 — Remove bridges.** After all callers are updated and tests pass, delete the bridge symlinks.

**Do not use big-bang:** the session-startup hook alone fires on every Claude Code invocation and would break the ADR scan immediately. The `cos release` Go binary break would surface only at release time — a silent failure. The self-improvement loop misdirection could silently write reports to nowhere for days.

## Decision Outcome (2026-05-12)

Operator chose **Sprint 1 quick-wins** (INDEX.md + AGENTS.md + ADR INDEX + dedupe archive) over the vault-numbered rename. The migration described above is shelved pending evidence that the physical structure (vs. the new navigation layer) is the bottleneck.

See commits `04d2a6ca` and `b144c3bc` for the Sprint 1 implementation.
