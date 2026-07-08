---
type: concept-synthesis
source: docs/04-Concepts/architecture/rust-migration-script-inventory.md
provenance: "Classifies every tracked Python, Go, and Bash implementation surface before any Rust migration decision; explicitly a migration-planning artifact, not a rewrite mandate."
---

## What it is
Migration-planning inventory (2026-05-12) classifying every tracked `.py`/`.go`/`.sh` file into one of 6 Rust-migration-readiness categories, separating code worth evaluating for a Rust core from code that should stay as tests, glue, generators, or legacy.

## Key mechanics
- Categories (exactly 6): `core_runtime`, `CLI`, `diagnostics`, `test_helpers`, `generators`, `legacy`. Total classified: **2,501 files**.
- Summary counts (files / approx LOC): `test_helpers` 1,201 / 237,404 (keep as tests, port only golden fixtures); `core_runtime` 871 / 214,003 (highest-value candidate, migrate behind stable boundaries); `CLI` 214 / 50,259 (strong candidate for one portable `cos` binary); `diagnostics` 170 / 35,268 (port hot/deterministic scanners first); `generators` 30 / 7,056 (defer until output schemas freeze); `legacy` 15 / 1,330 (do not port).
- Representative surfaces per category: `core_runtime` = `hooks/`, `hooks/_lib/`, `lib/`, `internal/`, `pkg/`, `packages/`, selected `scripts/cos_*.py`; `CLI` = `cmd/cos/`, `cmd/cos-dispatch/`, `bin/`, `install.sh`; `diagnostics` = `scripts/*audit*.py`, `*doctor*.sh`, `*validate*.py`, `*coverage*.py`, `*benchmark*.py`, `workflows/`, `primitive_coverage/`; `test_helpers` = `tests/`, `scripts/test-*`, `*smoke*`; `generators` = `scripts/generate_*.py`, `regen_*.py`, `backfill_*.py`, `migrate_*.py`, `templates/`; `legacy` = `archive/`, `docs/*.sh`, demo/lab/sandbox scripts.
- Recommended waves: Wave0 establish a minimal Rust workspace boundary (config/manifest loading, deterministic scanning, JSONL writing, rule serialization, stable CLI contracts) — no rewrite yet; Wave1 one deterministic diagnostics scanner (readiness/exposure/config scanners); Wave2 CLI consolidation, gated on 3 conditions (packaging benefit, dedup via core-library reuse, or Go maintenance blocking velocity); Wave3 core runtime extraction in order (parsing/validation -> read-only scans -> metrics serialization -> state transitions -> hook adapters last); Wave4 hook shell thinning (replace embedded logic with calls to compiled Rust tools only after parity evidence).
- Explicit "Do Not Start With": rewriting all `tests/` into Rust; replacing Bash hook entrypoints before the harness contract is proven; porting one-off migrations/backfills; porting archived/demo/lab surfaces; rewriting the Go CLI solely for language uniformity.
- Wave 1 concrete selection: `cos-script-exposure-audit-rs`, a parity implementation of the ADR-283 script exposure diagnostic — chosen for deterministic I/O, existing Python test coverage, high operational value (protects agentic primitive discoverability), and low side-effect risk (read-only, report-oriented).
- Rust acceptance criteria for the Wave-1 slice: `cargo test -p cos-script-exposure-audit-rs` passes; `cargo clippy -p cos-script-exposure-audit-rs -- -D warnings` passes; existing Python script-exposure tests still pass; Rust and Python JSON summaries match on the shared fixture with and without dispositions. The Python CLI remains production/default; the Rust CLI is a parity candidate only.

## Relations & where used
Source command: `git ls-files | grep -E '\.(py|go|sh)$'`. Machine-readable inventory: `docs/06-Daily/reports/rust-migration-script-inventory-2026-05-12.csv`. Related to ADR-283 (script exposure audit).

## Status / caveats
Working conclusion: staged extraction of the stable core only, not a full repository rewrite — "Rust for portable core and high-signal diagnostics; Go CLI only if consolidation pays for itself; Python for flexible generators and evolving audits; Bash as thin harness boundary." Wave 1 is selected but not stated as completed within this document.
