# Primitive Duplication Audit — Latest

Generated: `2026-06-16T13:54:31.706285+00:00`

## Summary

- Files scanned: 1041
- Findings: 21
- By kind: `{"python-function-repeat": 21}`
- By common home: `{"lib/": 21}`
- By consumer relevance: `{"so-local-first": 21}`

## Top Candidates

| Kind | Classification | Similarity | Left | Right | Recommendation | Common home | Consumer relevance |
|---|---|---:|---|---|---|---|---|
| python-function-repeat | candidate | 1.0 | `scripts/cos_agent_flicker_report.py::_utc_now` | `scripts/cos_instance_init.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::append_jsonl` | `scripts/cos_lean_skillopt.py::append_jsonl` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::append_jsonl` | `scripts/cos_process_loop.py::append_jsonl` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::read_json` | `scripts/cos_lean_skillopt.py::read_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::read_json` | `scripts/cos_loop.py::load_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::read_json` | `scripts/cos_process_loop.py::load_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::rel` | `scripts/cos_efficiency_primitives.py::rel` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::rel` | `scripts/cos_lean_skillopt.py::rel` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::sanitize_id` | `scripts/cos_lean_skillopt.py::sanitize_id` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::sanitize_id` | `scripts/cos_process_loop.py::sanitize_id` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::sha256_bytes` | `scripts/cos_lib_symlink_invariant_audit.py::_sha256` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::utc_now` | `scripts/cos_lean_skillopt.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::utc_now` | `scripts/cos_loop.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::utc_now` | `scripts/cos_process_loop.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::write_json` | `scripts/cos_lean_skillopt.py::write_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_artifact_workflow.py::write_json` | `scripts/cos_process_loop.py::write_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_efficiency_primitives.py::main` | `scripts/cos_lean_skillopt.py::main` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_lean_skillopt.py::emit` | `scripts/cos_process_loop.py::output` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_loop.py::load_jsonl` | `scripts/cos_process_loop.py::load_jsonl` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_loop.py::main` | `scripts/cos_process_loop.py::main` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_so_impact_eval.py::utc_run_id` | `scripts/state_retention_audit.py::stamp` | extract-common-python-helper | `lib/` | so-local-first |

## Interpretation

- Treat findings as refactor candidates, not automatic rewrite instructions.
- Keep intentional duplication only when isolation, portability, or harness-specific behavior is documented.
- Promote repeated projected primitive behavior into shared rules/skills/hooks only after ACC projection proof exists.
