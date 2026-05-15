# Primitive Scope Classifier — Iteration 020: hooks sub-batch 001

Date: 2026-05-15

## Goal

Resolve the first 12 `hooks/` rows from the declared-`both` `insufficient-metadata` bucket, using the ADR-314 classification rubric row by row.

## Decision

All 12 rows in this batch are `os-only`. They are hook runtime support libraries/helpers for operating Cognitive OS hooks, not standalone repository-construction guidance for adopter projects. Some are portable across harnesses, but portability of the COS hook runtime is not the same as a `both` agentic primitive surface.

## Rows

| Hook support file | Decision | Evidence |
|---|---:|---|
| `hooks/_lib/artifact-status.sh` | `os-only` | Loads COS persisted test/coverage artifacts for governance hooks. |
| `hooks/_lib/cache.sh` | `os-only` | Stores hook scan cache under `.cognitive-os/cache` for COS hook execution. |
| `hooks/_lib/circuit-breaker.sh` | `os-only` | Implements COS auto-repair circuit breaker state under `.cognitive-os` metrics. |
| `hooks/_lib/common.sh` | `os-only` | Shared runtime resolver for Cognitive OS hooks and COS config/session paths. |
| `hooks/_lib/context_budget_lib.sh` | `os-only` | Accounts ADR-186 context budget for COS hook `additionalContext` output. |
| `hooks/_lib/dispatch_gate_check.py` | `os-only` | Single-pass implementation for COS dispatch-gate hook and COS agent/task limits. |
| `hooks/_lib/execute-repair.sh` | `os-only` | Executes COS remediation/repair hook workflow. |
| `hooks/_lib/file_checker.sh` | `os-only` | Shared file-check helper for COS hooks. |
| `hooks/_lib/hook-pipe.sh` | `os-only` | Stores cross-hook values in `.cognitive-os/.hook-pipe` runtime state. |
| `hooks/_lib/normalize-stdin.sh` | `os-only` | Normalizes coding-harness hook JSON for COS hook runtime adapters. |
| `hooks/_lib/portable.sh` | `os-only` | Portable shell helper sourced by COS hook/runtime scripts, not a standalone project primitive. |
| `hooks/_lib/push-collision-check.sh` | `os-only` | Push collision detector library invoked by COS hook gates. |

## Result

Actual after classifier regeneration:

- `hooks` unknown debt: 36 → 24.
- total unknown debt: 231 → 219.
- `by_suggested_scope`: `both=214`, `os-only=661`, `project=94`, `unknown=219`.
- 12 stale `both` markers corrected to `os-only`.

## Next work

Continue with the next hook support/runtime sub-batch, preserving the distinction between COS runtime portability and `both` repository-agnostic primitive semantics.
