# Rust Transpiler Evaluation Report

Schema: `rust-transpiler-eval/v1`  
Project: `<repo-root>`  

## Summary

| Tool | Candidate | Status | Exit | Compile | Parity | Manual fix cost | Generated files |
|---|---|---:|---:|---:|---|---|---:|
| py2many | `scripts/agentic_mastery_summary.py` | partial-output-with-tool-errors | 1 | 101 | not-checkable | high | 1 |
| tnk | `scripts/agentic_mastery_summary.py` | partial-output-with-tool-errors | 1 | 101 | not-checkable | high | 13 |
| depyler | `scripts/agentic_mastery_summary.py` | generated-but-compile-fails | 0 | 101 | not-checkable | medium | 1 |
| py2many | `scripts/regen_catalog_bullets.py` | partial-output-with-tool-errors | 1 | n/a | not-checkable | high | 1 |
| tnk | `scripts/regen_catalog_bullets.py` | no-usable-output | 1 | n/a | not-checkable | blocked | 0 |
| depyler | `scripts/regen_catalog_bullets.py` | generated-but-compile-fails | 0 | 101 | not-checkable | medium | 1 |
| py2many | `scripts/backfill_cost_events.py` | partial-output-with-tool-errors | 1 | n/a | not-checkable | high | 1 |
| tnk | `scripts/backfill_cost_events.py` | no-usable-output | 1 | n/a | not-checkable | blocked | 0 |
| depyler | `scripts/backfill_cost_events.py` | generated-but-compile-fails | 0 | 101 | not-checkable | medium | 1 |

## Decision Rule

A transpiler can become an official migration assistant only when it produces compiling Rust with low or medium manual-fix cost on representative fixtures and the Python↔Rust golden parity lane passes.

No generated Rust from this lane replaces source code automatically.
