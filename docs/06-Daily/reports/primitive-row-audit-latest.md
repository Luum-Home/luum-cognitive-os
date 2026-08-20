# Primitive Row Audit — Latest

> verify: .venv/bin/python3 scripts/primitive_row_audit.py

## Summary

| Family | Total | Proven | Partial | Aspirational | Harmful |
|---|---:|---:|---:|---:|---:|
| hooks | 295 | 114 | 181 | 0 | 0 |
| metrics | 124 | 106 | 3 | 15 | 0 |
| rules | 132 | 131 | 1 | 0 | 0 |
| skills | 276 | 223 | 51 | 2 | 0 |

## High-Severity Rows

| Family | Name | Status | Evidence | Next action |
|---|---|---|---|---|
| hooks | `cos-session-start-projector.sh` | partial | events=SessionStart,projected; tested=False; emits_metric=False | add behavioral test |
