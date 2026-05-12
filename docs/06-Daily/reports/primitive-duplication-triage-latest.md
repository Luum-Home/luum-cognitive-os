# Primitive Duplication Triage — Latest

Generated: 2026-05-04

## Summary

Source report: `docs/reports/primitive-duplication-latest.json`.

| Common home | Kind | Count | Triage |
|---|---:|---:|---|
| `lib/` | `python-function-repeat` | 39 | Extract selectively; prioritize shared ledger/runtime helpers. |
| `hooks/_lib/` | `bash-function-repeat` | 6 | Extract first; duplicated hook artifact status loaders affect runtime gates. |
| `scripts/_lib/` | `bash-function-repeat` | 4 | Extract local daemon lifecycle helpers. |
| `templates/ or lib/` | `exact-copy` | 1 | Intentional compatibility alias; do not extract. |

## Extract first

1. **Hook artifact-status loaders** → `hooks/_lib/`
   - `hooks/auto-verify.sh::_load_test_artifact_status`
   - `hooks/dod-gate.sh::_load_test_artifact_status`
   - `hooks/auto-verify.sh::_load_coverage_artifact_status`
   - `hooks/dod-gate.sh::_load_coverage_artifact_status`

2. **Local daemon shell helpers** → `scripts/_lib/`
   - `scripts/cos-postgres-local.sh::_daemon_alive`
   - `scripts/cos-valkey-local.sh::_daemon_alive`
   - `scripts/cos-valkey-local.sh::_port_in_use`

3. **Ledger CLI path and JSONL helpers** → `lib/`
   - `scripts/agent_work_ledger.py::project_dir`
   - `scripts/approval_ledger.py::project_dir`
   - `scripts/claim_task.py::project_dir`
   - `scripts/cross_session_reconciler.py::project_dir`
   - `scripts/resource_lease.py::project_dir`
   - `scripts/agent_work_ledger.py::read_events`
   - `scripts/cross_session_reconciler.py::read_jsonl`

4. **Shared timestamp parsing** → `lib/`
   - `scripts/cos_false_positive_ledger.py::parse_ts`
   - `scripts/cos_governance_roi.py::parse_ts`

5. **Primitive readiness shared loaders/counts** → `lib/` only after schema review
   - `scripts/primitive_family_readiness_ledger.py::load_lifecycle`
   - `scripts/primitive_readiness_ledger.py::load_lifecycle`
   - `scripts/primitive_family_readiness_ledger.py::family_counts`
   - `scripts/primitive_readiness_ledger.py::family_counts`

## Do not extract yet

- `hooks/reaper-heartbeat.sh` ↔ `hooks/reaper-daemon-launcher.sh`: `reaper-heartbeat.sh` is a symlink compatibility alias, not duplicate implementation debt.
- Tiny `main`, `read_json`, `rel`, `now_iso`, or `get_project_root` helpers: low ROI unless they are already part of a broader helper extraction.
- `row_to_dict` across readiness ledgers: extract only if script and family readiness rows share a formal schema.
- `hooks/auto-verify.sh::found` ↔ `hooks/completion-gate.sh::found`: likely parser artifact around awk state, not a shell helper to extract.

## Acceptance criteria for extraction slices

1. Extract one cluster per commit.
2. Keep behavioral tests for the touched hooks/scripts passing.
3. Regenerate `docs/reports/primitive-duplication-latest.*` after extraction.
4. Do not mark a duplicate as resolved unless the report count drops or an intentional-duplication allowlist is added.
