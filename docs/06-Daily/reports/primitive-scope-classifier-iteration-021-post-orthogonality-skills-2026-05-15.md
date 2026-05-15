# Primitive Scope Classifier — Iteration 021: post-orthogonality skills cleanup

Date: 2026-05-15

## Goal

After fixing the classifier so `distribution` is orthogonal to `SCOPE`, resolve the two skills that returned to the unknown queue because they lacked explicit scope metadata.

## Rows

| Skill | Decision | Evidence |
|---|---:|---|
| `skills/agent-control/SKILL.md` | `os-only` | Controls live COS agents via `scripts/orchestrator.py`, `.cognitive-os/agent-bus`, Valkey, and COS hook inbound guards. |
| `skills/primitive-harness-coverage/SKILL.md` | `os-only` | Measures COS primitive implementation coverage across harness surfaces for COS maintainers. |

## Result

Actual after classifier regeneration:

- `skills` unknown debt: 2 → 0.
- total unknown debt: 428 → 426 before any additional hook/script/rule cleanup.
- `by_suggested_scope`: `both=163`, `os-only=487`, `project=112`, `unknown=426`.
- 2 stale `both` markers corrected to `os-only`.

## Note

This cleanup confirms the orthogonality fix: `distribution` no longer provides scope evidence by itself; these two rows needed explicit maintainer-only consumer/lifecycle evidence.
