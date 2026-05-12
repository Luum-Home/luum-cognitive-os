# Rust Migration Script Inventory — 2026-05-12

## Purpose

This inventory classifies the tracked Python, Go, and Bash implementation surfaces before any Rust migration. It is intentionally a migration-planning artifact, not a final rewrite mandate.

The goal is to separate code that is worth evaluating for a Rust core from code that should remain as tests, glue, generators, or archived/legacy support.

## Acceptance Criteria

1. Every tracked `*.py`, `*.go`, and `*.sh` file is classified once in `docs/06-Daily/reports/rust-migration-script-inventory-2026-05-12.csv`.
2. Categories are limited to: `core_runtime`, `CLI`, `diagnostics`, `test_helpers`, `generators`, `legacy`.
3. No row is left unclassified.
4. The inventory identifies which classes are Rust-first candidates and which should stay outside the first migration wave.

## Inventory Scope

Generated from tracked files only with:

```bash
git ls-files | grep -E '\.(py|go|sh)$'
```

This excludes untracked local caches, virtualenvs, vendored reference corpora, and build outputs.

Machine-readable inventory:

- `docs/06-Daily/reports/rust-migration-script-inventory-2026-05-12.csv`

## Summary Counts

| Category | Total files | Python | Go | Bash | Approx. LOC | Rust migration posture |
|---|---:|---:|---:|---:|---:|---|
| `test_helpers` | 1201 | 1164 | 0 | 37 | 237404 | Keep mostly as tests; port only golden-test fixtures needed by Rust crates. |
| `core_runtime` | 871 | 471 | 49 | 351 | 214003 | Highest-value Rust candidate, but migrate behind stable boundaries. |
| `CLI` | 214 | 49 | 125 | 40 | 50259 | Strong Rust candidate if the product wants one portable `cos` binary. |
| `diagnostics` | 170 | 132 | 0 | 38 | 35268 | Port hot scanners and deterministic validators first; keep low-frequency audits in Python. |
| `generators` | 30 | 21 | 0 | 9 | 7056 | Keep in Python/Bash until output schemas freeze. |
| `legacy` | 15 | 1 | 0 | 14 | 1330 | Do not port unless resurrected into active workflows. |

Total classified files: **2501**.

## Category Definitions

### `core_runtime`

Runtime code that participates in hook execution, state management, provider/runtime normalization, portable projection, packaged runtime behavior, or shared script libraries.

Representative surfaces:

- `hooks/` — Claude/Codex lifecycle hook boundary. Keep the outer shell contract thin; port reusable logic below it.
- `hooks/_lib/` — shared shell runtime helpers.
- `lib/` — Python runtime modules for metrics, routing, config, state, portability, and governance.
- `internal/` and `pkg/` — Go runtime/provider/hook model packages.
- `packages/` — packaged runtime/projection assets.
- selected `scripts/cos_*.py` and `scripts/cos-*.sh` runtime orchestrators.

Rust posture: **candidate**, but not by blind rewrite. First extract stable library boundaries for config loading, manifest parsing, filesystem scanning, event/metrics serialization, and deterministic rule evaluation.

### `CLI`

Operator-facing commands and package-manager surfaces.

Representative surfaces:

- `cmd/cos/` — Go CLI package manager, installer, wizard, registry, audit/status commands.
- `cmd/cos-dispatch/` — dispatch/review command surface.
- `bin/`, `install.sh`, and selected `scripts/cos-*` command wrappers.

Rust posture: **candidate** if the desired product shape is a single portable `cos` binary. The existing Go CLI is already a typed compiled surface, so Rust should replace it only if the team wants one Rust workspace for core + CLI, or if distribution/embedding benefits justify the rewrite.

### `diagnostics`

Audits, doctors, validators, reports, coverage tools, benchmarks, readiness ledgers, and proof generators.

Representative surfaces:

- `scripts/*audit*.py`
- `scripts/*doctor*.sh`
- `scripts/*validate*.py`
- `scripts/*coverage*.py`
- `scripts/*benchmark*.py`
- `workflows/`
- `primitive_coverage/`

Rust posture: **selective candidate**. Port scanners that are deterministic, frequently run, or expensive. Keep exploratory audits in Python until rules stabilize.

### `test_helpers`

Unit/behavior/integration tests, smoke runners, adversarial scenario runners, and test-support wrappers.

Representative surfaces:

- `tests/`
- `scripts/test-*`
- `scripts/*smoke*`
- `scripts/pytest-with-summary.sh`
- package-local test helpers.

Rust posture: **not first-wave**. Keep tests as the safety net for migration. Add Rust golden tests that compare outputs against current Python/Go behavior before replacing production paths.

### `generators`

Code/docs/config generators, migration scripts, backfills, renderers, and template composers.

Representative surfaces:

- `scripts/generate_*.py`
- `scripts/regen_*.py`
- `scripts/backfill_*.py`
- `scripts/migrate_*.py`
- `templates/`

Rust posture: **defer** unless the generator becomes runtime-critical. Python is acceptable for schema churn and one-off backfills.

### `legacy`

Archived, demo, lab, sandbox, documentation-embedded, or environment wrapper scripts that should not drive a Rust migration.

Representative surfaces:

- `archive/`
- `docs/*.sh`
- demo/lab/sandbox scripts.

Rust posture: **do not port** unless a file is promoted back into a live agentic primitive or maintainer workflow.

## Recommended Rust Migration Waves

### Wave 0 — no rewrite, establish Rust boundary

Create a minimal Rust workspace only after choosing one narrow slice. Do not delete Python/Go/Bash paths yet.

Target traits/contracts:

- config/manifest loading
- deterministic repo scanning
- JSONL metrics/event writing
- rule/audit result serialization
- stable CLI output contracts

### Wave 1 — diagnostics scanner slice

Best first Rust target: one deterministic diagnostic scanner with clear fixtures and stable output.

Good candidates:

- primitive/readiness scanners
- script exposure scanners
- config/manifest validators
- filesystem inventory scanners

Why: these are easier to golden-test, have fewer side effects, and prove Rust value without disrupting hook runtime.

### Wave 2 — CLI consolidation

If Wave 1 proves useful, evaluate whether `cmd/cos/` should remain Go or become a Rust CLI.

Decision gate:

- Rust binary packaging materially improves install/support; or
- Rust core library reuse eliminates duplicate logic; or
- Go CLI maintenance is blocking product velocity.

If none are true, keep the Go CLI and expose Rust diagnostics as subprocess/library tools.

### Wave 3 — core runtime extraction

Move reusable Python runtime logic from `lib/` only after tests and output contracts are stable.

Preferred order:

1. pure parsing/validation
2. read-only repo scans
3. metrics serialization
4. state transitions with golden fixtures
5. hook-facing adapters last

### Wave 4 — hook shell thinning

Keep shell hooks as lifecycle entrypoints where the harness expects shell scripts. Replace embedded business logic with calls to compiled Rust tools only after the Rust path has parity evidence.

## Do Not Start With

- Rewriting all `tests/` into Rust.
- Replacing Bash hook entrypoints before the harness contract is proven.
- Porting one-off migrations/backfills.
- Porting archived/demo/lab surfaces.
- Rewriting the existing Go CLI solely for language uniformity.

## Working Conclusion

A Rust migration is viable and likely valuable, but only as a staged extraction of the stable core. The inventory suggests the first Rust work should target deterministic diagnostics and runtime libraries, not a full repository rewrite.

The strongest near-term posture is:

> Rust for portable core and high-signal diagnostics; Go CLI only if consolidation pays for itself; Python for flexible generators and evolving audits; Bash as thin harness boundary.

## Wave 1 Selection — ADR-283 Script Exposure Audit

The first Rust slice is `cos-script-exposure-audit-rs`, a parity implementation of the ADR-283 script exposure diagnostic.

Why this scanner first:

- deterministic input/output: JSON scripts ledger plus optional YAML dispositions manifest
- already covered by Python unit and behavior tests
- high operational value because it protects agentic primitive discoverability
- low side-effect risk because it is read-only and report-oriented
- useful migration shape: native Rust library plus CLI, while the existing Python implementation remains authoritative until parity is proven on real ledgers

Initial Rust acceptance criteria:

1. `cargo test -p cos-script-exposure-audit-rs` passes.
2. `cargo clippy -p cos-script-exposure-audit-rs -- -D warnings` passes.
3. Existing Python script-exposure tests still pass.
4. Rust JSON summaries match Python JSON summaries on the shared fixture with and without dispositions.

The Python CLI remains the production/default path for now. The Rust CLI is a parity candidate, not yet a replacement.
