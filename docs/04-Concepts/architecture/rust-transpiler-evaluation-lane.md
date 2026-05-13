# Rust Transpiler Evaluation Lane

## Purpose

Evaluate open-source Python-to-Rust transpilers as migration assistants without letting generated code replace Cognitive OS source files automatically.

This lane exists because a full Python/Go/Bash-to-Rust rewrite is too risky, while selected transpilers may still reduce exploration cost for small, deterministic scripts.

## Waves

### Wave 1.1 — Tool Trial

Run at least two Python-to-Rust transpilers against three small tracked Python scripts. The current lane includes three tools: `py2many`, `tnk`, and `depyler`.

Initial tools:

- `py2many` — Python-to-many transpiler with Rust backend.
- `tnk` / Tsuchinoko — type-hinted Python-to-Rust transpiler.
- `depyler` — annotated Python-to-Rust transpiler with `depyler transpile input.py -o output.rs` CLI support.

Initial candidates:

- `scripts/agentic_mastery_summary.py`
- `scripts/regen_catalog_bullets.py`
- `scripts/backfill_cost_events.py`

### Wave 1.2 — Measure

For each tool and script, record:

- transpiler exit code
- generated files count
- Rust compile/check exit code when a checkable Rust target exists
- stdout/stderr excerpts
- manual-fix-cost estimate: `low`, `medium`, `high`, or `blocked`

### Wave 1.3 — Decide

A transpiler can become an official migration assistant only when it produces compiling Rust with low or medium manual-fix cost on representative fixtures.

### Wave 1.4 — Golden Tests Required

No generated Rust may replace Python source unless a Python↔Rust golden parity test exists for the relevant behavior.

## Operator Command

```bash
PATH="/path/to/py2many/bin:/path/to/tnk/bin:/path/to/depyler/bin:$PATH" \
  scripts/cos-rust-transpiler-eval \
  --json-out docs/06-Daily/reports/rust-transpiler-eval-2026-05-12.json \
  --md-out docs/06-Daily/reports/rust-transpiler-eval-2026-05-12.md
```

The command does not install tools. Tool installation remains an explicit operator action so dependency adoption is not hidden inside the lane.

## Current Evaluation Result — 2026-05-12

Report:

- `docs/06-Daily/reports/rust-transpiler-eval-2026-05-12.md`
- `docs/06-Daily/reports/rust-transpiler-eval-2026-05-12.json`

Outcome:

- `py2many` generated partial Rust for all three candidates, but each run exited non-zero and required high manual-fix cost.
- `tnk` generated a Cargo project for `scripts/agentic_mastery_summary.py` only after `--project` retry, but `cargo check` failed; the other two candidates were blocked by unsupported syntax or parse errors.
- Neither tool qualifies as an official migration assistant yet.


## Scope Correction

The initial script-mode run tests direct applicability to real COS scripts. It does not prove what the tools can do on their intended subset.

A fair second pass uses capability fixtures:

- pure functions over ints/lists
- simple parsing without external IO
- list/dict transformations

Run capability mode with:

```bash
PATH="/path/to/py2many/bin:/path/to/tnk/bin:/path/to/depyler/bin:$PATH"   scripts/cos-rust-transpiler-eval --mode capability   --json-out docs/06-Daily/reports/rust-transpiler-capability-eval-2026-05-12.json   --md-out docs/06-Daily/reports/rust-transpiler-capability-eval-2026-05-12.md
```

Capability report:

- `docs/06-Daily/reports/rust-transpiler-capability-eval-2026-05-12.md`
- `docs/06-Daily/reports/rust-transpiler-capability-eval-2026-05-12.json`
- `docs/06-Daily/reports/rust-transpiler-scope-correction-2026-05-12.md`

Current capability finding: `tnk` passes a narrow pure int/list fixture with Rust compile and stdout parity; neither previously evaluated tool handles the broader parsing/dict fixtures well enough for official adoption yet. The committed 2026-05-12 reports predate Depyler wiring; rerun script-mode and capability-mode with `depyler` installed before making any Depyler adoption claim.

## Decision

Keep transpilers in lab/evaluation status. Continue manual Rust slices with golden parity tests as the production migration method. Depyler is now part of the lane as a third candidate, but generated code still has no replacement authority without compile and parity evidence.
