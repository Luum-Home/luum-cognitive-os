# Rust Transpiler Scope Correction — 2026-05-12

## Correction

The first transpiler evaluation answered only this question:

> Can `py2many` or `tnk` directly translate three real Cognitive OS Python scripts with filesystem paths, internal imports, exceptions, context managers, and repo-specific behavior?

It did **not** fairly answer this different question:

> What subset of Python do these tools handle well enough to help with Rust migration drafts?

The first answer was negative for current COS scripts. That result must not be overstated as a general failure of the tools.

## Fair Capability Probe Added

A second capability-mode probe now evaluates minimal fixtures that intentionally avoid repo IO and internal imports:

- `tests/fixtures/rust_transpiler_eval/pure_ints_lists.py` — pure integer/list functions.
- `tests/fixtures/rust_transpiler_eval/simple_parse_no_io.py` — simple string parsing with no external IO.
- `tests/fixtures/rust_transpiler_eval/list_dict_transform.py` — list/dict transformation.

Report:

- `docs/06-Daily/reports/rust-transpiler-capability-eval-2026-05-12.md`
- `docs/06-Daily/reports/rust-transpiler-capability-eval-2026-05-12.json`

## Capability Result

| Tool | Capability result |
|---|---|
| `tnk` / Tsuchinoko | Passed the pure ints/lists fixture: generated Rust compiled and matched Python stdout. Failed compile on parsing and dict/string transformation fixtures. |
| `py2many` | Generated Rust for all three capability fixtures, but none compiled without manual fixes. |
| `depyler` | Generated Rust for all three capability fixtures after the 2026-05-14 lane update, but none compiled without manual fixes. |

## Updated Decision

- `tnk` **does** have a useful narrow subset: pure, type-hinted integer/list algorithms.
- `tnk` is not yet suitable for general COS scripts, string parsing, or dict-heavy transforms without manual repair.
- `py2many` remains useful as a draft/learning generator only; this probe did not produce compiling Rust for the selected fixtures.
- `depyler` is also lab-only after the 2026-05-14 rerun: it generated code, but the selected fixtures did not compile under the lane probe.
- No tool becomes an official replacement path until golden Python↔Rust parity exists for the target behavior.

## Operational Rule

Use transpilers only in lab mode unless all of the following are true:

1. generated Rust compiles;
2. generated Rust stdout/output matches Python on fixture inputs;
3. manual-fix-cost is `low` or explicitly accepted;
4. the migration target has a golden parity test before replacement.
