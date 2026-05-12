# Rust Transpiler Evaluation Report

Schema: `rust-transpiler-eval/v1`  
Project: `<repo-root>`  

## Summary

| Tool | Candidate | Status | Exit | Compile | Manual fix cost | Generated files |
|---|---|---:|---:|---:|---|---:|
| py2many | `scripts/agentic_mastery_summary.py` | partial-output-with-tool-errors | 1 | 101 | high | 1 |
| tnk | `scripts/agentic_mastery_summary.py` | partial-output-with-tool-errors | 1 | 101 | high | 13 |
| py2many | `scripts/regen_catalog_bullets.py` | partial-output-with-tool-errors | 1 | n/a | high | 1 |
| tnk | `scripts/regen_catalog_bullets.py` | no-usable-output | 1 | n/a | blocked | 0 |
| py2many | `scripts/backfill_cost_events.py` | partial-output-with-tool-errors | 1 | n/a | high | 1 |
| tnk | `scripts/backfill_cost_events.py` | no-usable-output | 1 | n/a | blocked | 0 |

## Decision Rule

A transpiler can become an official migration assistant only when it produces compiling Rust with low or medium manual-fix cost on representative fixtures and the Python↔Rust golden parity lane passes.

No generated Rust from this lane replaces source code automatically.
