# Rust Transpiler Evaluation Report

Schema: `rust-transpiler-eval/v1`  
Project: `<repo-root>`  

## Summary

| Tool | Candidate | Status | Exit | Compile | Parity | Manual fix cost | Generated files |
|---|---|---:|---:|---:|---|---|---:|
| py2many | `tests/fixtures/rust_transpiler_eval/pure_ints_lists.py` | generated-but-compile-fails | 0 | 101 | not-checkable | medium | 1 |
| tnk | `tests/fixtures/rust_transpiler_eval/pure_ints_lists.py` | generated-and-compiles | 0 | 0 | pass | low | 1 |
| depyler | `tests/fixtures/rust_transpiler_eval/pure_ints_lists.py` | generated-but-compile-fails | 0 | 101 | not-checkable | medium | 1 |
| py2many | `tests/fixtures/rust_transpiler_eval/simple_parse_no_io.py` | generated-but-compile-fails | 0 | 101 | not-checkable | medium | 1 |
| tnk | `tests/fixtures/rust_transpiler_eval/simple_parse_no_io.py` | generated-but-compile-fails | 0 | 101 | not-checkable | medium | 1 |
| depyler | `tests/fixtures/rust_transpiler_eval/simple_parse_no_io.py` | generated-but-compile-fails | 0 | 101 | not-checkable | medium | 1 |
| py2many | `tests/fixtures/rust_transpiler_eval/list_dict_transform.py` | generated-but-compile-fails | 0 | 101 | not-checkable | medium | 1 |
| tnk | `tests/fixtures/rust_transpiler_eval/list_dict_transform.py` | generated-but-compile-fails | 0 | 101 | not-checkable | medium | 1 |
| depyler | `tests/fixtures/rust_transpiler_eval/list_dict_transform.py` | generated-but-compile-fails | 0 | 101 | not-checkable | medium | 1 |

## Decision Rule

A transpiler can become an official migration assistant only when it produces compiling Rust with low or medium manual-fix cost on representative fixtures and the Python↔Rust golden parity lane passes.

No generated Rust from this lane replaces source code automatically.
