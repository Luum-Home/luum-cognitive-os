# Rust Transpiler Evaluation Lane

## Purpose

Evaluate open-source Python-to-Rust transpilers as migration assistants without letting generated code replace Cognitive OS source files automatically.

This lane exists because a full Python/Go/Bash-to-Rust rewrite is too risky, while selected transpilers may still reduce exploration cost for small, deterministic scripts.

## Waves

### Wave 1.1 — Tool Trial

Run at least two Python-to-Rust transpilers against three small tracked Python scripts.

Initial tools:

- `py2many` — Python-to-many transpiler with Rust backend.
- `tnk` / Tsuchinoko — type-hinted Python-to-Rust transpiler.

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
PATH="/path/to/py2many/bin:/path/to/tnk/bin:$PATH" \
  scripts/cos-rust-transpiler-eval \
  --json-out docs/reports/rust-transpiler-eval-2026-05-12.json \
  --md-out docs/reports/rust-transpiler-eval-2026-05-12.md
```

The command does not install tools. Tool installation remains an explicit operator action so dependency adoption is not hidden inside the lane.

## Current Evaluation Result — 2026-05-12

Report:

- `docs/reports/rust-transpiler-eval-2026-05-12.md`
- `docs/reports/rust-transpiler-eval-2026-05-12.json`

Outcome:

- `py2many` generated partial Rust for all three candidates, but each run exited non-zero and required high manual-fix cost.
- `tnk` generated a Cargo project for `scripts/agentic_mastery_summary.py` only after `--project` retry, but `cargo check` failed; the other two candidates were blocked by unsupported syntax or parse errors.
- Neither tool qualifies as an official migration assistant yet.

## Decision

Keep transpilers in lab/evaluation status. Continue manual Rust slices with golden parity tests as the production migration method.
