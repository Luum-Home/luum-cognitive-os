# Rust Migration Routes

## Purpose

Cognitive OS may use Rust for selected high-signal surfaces, but Rust is not a blanket rewrite mandate. This contract defines the two sanctioned production routes after the 2026-05-12 migration inventory and transpiler review.

## Acceptance Criteria

1. Production Rust replacements preserve the Python/Go/Bash behavior through golden parity tests before promotion.
2. Transpilers remain lab-only unless generated Rust compiles, matches the source behavior, and has accepted manual-fix cost.
3. Hot-path Rust is introduced through an explicit Python extension boundary when a whole-script port is over-engineering.
4. Shell hooks remain thin harness entrypoints until a compiled replacement has parity evidence and a safe rollback path.

## Route A — Manual Rust Crate with Golden Parity

Use this route for complete deterministic diagnostics, scanners, validators, and report generators.

Pattern:

1. Keep the existing Python/Go/Bash implementation authoritative.
2. Create a Rust crate with library logic plus a CLI wrapper.
3. Add fixture parity tests for small synthetic cases.
4. Add real-ledger or real-report golden parity against the current production implementation.
5. Promote only after full JSON/output parity is stable and operator-facing differences are intentional.

Current reference implementation:

- `crates/cos-script-exposure-audit-rs` mirrors `scripts/cos-script-exposure-audit`.
- `crates/cos-script-exposure-audit-rs/tests/parity.rs` includes fixture tests and a real-ledger Python↔Rust JSON equality test.

Use when:

- the tool is read-only or has easy rollback;
- inputs and outputs are deterministic;
- schemas are stable enough to test;
- whole-script ownership is simpler than an FFI boundary.

Do not use when:

- the behavior is still exploratory;
- the target is a one-off generator or backfill;
- there is no practical golden output to compare.

## Route B — PyO3 + maturin for Selective Hot Paths

Use this route when the product needs Rust performance or safety for a narrow Python hot path, but keeping the Python CLI/API is still the lowest-risk operator boundary.

Pattern:

1. Isolate the pure or near-pure hot function behind a stable Python call boundary.
2. Implement the hot path in Rust with PyO3 bindings.
3. Build and package with maturin.
4. Keep Python tests as the public behavior contract and add Rust unit tests for edge cases.
5. Provide a Python fallback or feature-gated import until the wheel path is proven across supported developer machines and CI.

Use when:

- only one parser/scorer/scanner loop needs Rust;
- the surrounding Python orchestration remains valuable;
- distribution through a Python wheel is simpler than replacing a whole CLI;
- the integration can be benchmarked and parity-tested independently.

Do not use when:

- a standalone Rust CLI is already the clearer operator interface;
- the Python boundary would obscure ownership, error handling, or install failures;
- the target has frequent schema churn.

## Lab Route — Transpilers as Draft Generators Only

The lab lane evaluates `py2many`, `tnk`, and `depyler` without granting any of them production replacement authority.

Transpiler output may be used as a draft only when all of the following are true:

1. generated Rust compiles;
2. generated Rust output matches Python on fixture inputs;
3. manual-fix-cost is `low` or explicitly accepted;
4. the migration target has a golden parity test before replacement.

`depyler` is included because its official docs describe `depyler transpile input.py -o output.rs` and single-command Rust generation, but those claims still need COS-local evidence before adoption. Source: [depyler 4.1.1 docs.rs](https://docs.rs/crate/depyler/latest).

## Route Selection Matrix

| Target | Preferred route | Why |
|---|---|---|
| Deterministic diagnostic CLI | Manual Rust crate + golden parity | Stable schemas and whole-report comparison are practical. |
| Expensive pure Python inner loop | PyO3 + maturin | Keeps Python orchestration while moving the hot path. |
| Bash hook entrypoint | Defer; thin shell around proven Rust tool | Harness lifecycle contracts remain shell-facing today. |
| One-off generator/backfill | Keep Python/Bash | Churn cost exceeds Rust value. |
| Transpiler-generated draft | Lab only | Output must pass compile, parity, and manual-review gates first. |

## Current Decision

Proceed with Wave 1 diagnostics via manual Rust crates and golden parity tests. Add PyO3 + maturin as the sanctioned selective hot-path route. Keep transpilers in the evaluation lane, with Depyler added as the third candidate, but do not promote generated code automatically.
