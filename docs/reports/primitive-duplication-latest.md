# Primitive Duplication Audit — Latest

Generated: `2026-05-04T21:53:53.214432+00:00`

## Summary

- Files scanned: 718
- Findings: 49
- By kind: `{"bash-function-repeat": 8, "exact-copy": 1, "python-function-repeat": 40}`
- By common home: `{"hooks/_lib/": 4, "lib/": 40, "scripts/_lib/": 4, "templates/ or lib/": 1}`
- By consumer relevance: `{"consumer-project-relevant": 7, "so-local-first": 42}`

## Top Candidates

| Kind | Similarity | Left | Right | Recommendation | Common home | Consumer relevance |
|---|---:|---|---|---|---|---|
| bash-function-repeat | 1.0 | `hooks/auto-verify.sh::found` | `hooks/completion-gate.sh::found` | extract-common-shell-helper | `hooks/_lib/` | consumer-project-relevant |
| bash-function-repeat | 1.0 | `hooks/destructive-git-blocker.sh::_git_blocker_is_agent_context` | `hooks/destructive-rm-blocker.sh::_is_agent_context` | extract-common-shell-helper | `hooks/_lib/` | consumer-project-relevant |
| bash-function-repeat | 1.0 | `hooks/edit-lock-drain-parked.sh::_session_id` | `hooks/edit-lock-process-negotiations.sh::_session_id` | extract-common-shell-helper | `hooks/_lib/` | consumer-project-relevant |
| bash-function-repeat | 1.0 | `hooks/edit-lock-drain-parked.sh::_session_id` | `scripts/edit-coop.sh::_session_id` | extract-common-shell-helper | `scripts/_lib/` | consumer-project-relevant |
| bash-function-repeat | 1.0 | `hooks/task-completed.sh::log_completion_event` | `hooks/task-created.sh::log_task_event` | extract-common-shell-helper | `hooks/_lib/` | consumer-project-relevant |
| bash-function-repeat | 1.0 | `scripts/cos-paperclip-local.sh::_daemon_alive` | `scripts/cos-postgres-local.sh::_daemon_alive` | extract-common-shell-helper | `scripts/_lib/` | so-local-first |
| bash-function-repeat | 1.0 | `scripts/cos-paperclip-local.sh::_daemon_alive` | `scripts/cos-valkey-local.sh::_daemon_alive` | extract-common-shell-helper | `scripts/_lib/` | so-local-first |
| bash-function-repeat | 1.0 | `scripts/cos-paperclip-local.sh::_port_in_use` | `scripts/cos-valkey-local.sh::_port_in_use` | extract-common-shell-helper | `scripts/_lib/` | so-local-first |
| exact-copy | 1.0 | `hooks/reaper-daemon-launcher.sh` | `hooks/reaper-heartbeat.sh` | extract-common | `templates/ or lib/` | consumer-project-relevant |
| python-function-repeat | 1.0 | `hooks/_lib/recap_adapter.py::_is_claude_code` | `hooks/_lib/task_panel_adapter.py::_is_claude_code` | extract-common-python-helper | `lib/` | consumer-project-relevant |
| python-function-repeat | 1.0 | `scripts/acc_pipeline.py::read_json` | `scripts/adr100_live_headroom_check.py::_load_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/acc_pipeline.py::read_json` | `scripts/derived_artifact_gate.py::normalized_json_file` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/acc_pipeline.py::read_json` | `scripts/harness_parity_audit.py::_load_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/acc_pipeline.py::write_json` | `scripts/cos_init.py::_write_json_if_changed` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/agent_work_ledger.py::main` | `scripts/approval_ledger.py::main` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/agent_work_ledger.py::main` | `scripts/claim_task.py::main` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/agent_work_ledger.py::main` | `scripts/cross_session_reconciler.py::main` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/agent_work_ledger.py::main` | `scripts/resource_lease.py::main` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/agent_work_ledger.py::project_dir` | `scripts/approval_ledger.py::project_dir` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/agent_work_ledger.py::project_dir` | `scripts/claim_task.py::project_dir` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/agent_work_ledger.py::project_dir` | `scripts/cross_session_reconciler.py::project_dir` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/agent_work_ledger.py::project_dir` | `scripts/resource_lease.py::project_dir` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/agent_work_ledger.py::read_events` | `scripts/cross_session_reconciler.py::read_jsonl` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/check_catalog_sync.py::get_project_root` | `scripts/check_hook_registration.py::get_project_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/check_catalog_sync.py::get_project_root` | `scripts/check_lib_wiring.py::get_project_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/check_catalog_sync.py::get_project_root` | `scripts/check_test_ratchet.py::get_project_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/claim_proof_audit.py::read_text` | `scripts/docs_execution_audit.py::read_text` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/claim_proof_audit.py::read_text` | `scripts/primitive_duplication_audit.py::read_text` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/claim_proof_audit.py::read_text` | `scripts/primitive_family_readiness_ledger.py::read_text` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/claim_proof_audit.py::read_text` | `scripts/primitive_readiness_ledger.py::read_text` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/claim_proof_audit.py::read_text` | `scripts/primitive_row_audit.py::read_text` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/claim_proof_audit.py::read_text` | `scripts/primitive_surface_reduce.py::read_text` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/claim_proof_audit.py::read_text` | `scripts/primitive_usage_map.py::read_text` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/claim_proof_audit.py::read_text` | `scripts/verify_plan_claims.py::_read` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/cos_closure_discipline_audit.py::rel` | `scripts/cos_flow_register.py::rel` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/cos_cross_instance_drill.py::_print` | `scripts/cos_cross_instance_learning.py::_print` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/cos_demotion_loop_audit.py::load_manifest` | `scripts/cos_manifest_tier_claim_audit.py::load_manifest` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/cos_executor.py::_project_dir` | `scripts/cos_watch.py::_project_dir` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/cos_false_positive_ledger.py::parse_ts` | `scripts/cos_governance_roi.py::parse_ts` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/cos_task_claims.py::now_iso` | `scripts/write_context_marker.py::_now_iso` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/docs_duplicate_audit.py::jaccard` | `scripts/primitive_duplication_audit.py::jaccard` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/docs_duplicate_audit.py::pair_key` | `scripts/primitive_duplication_audit.py::pair_key` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/docs_duplicate_audit.py::read_text` | `scripts/primitive_gap_snapshot.py::read_text` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/primitive_duplication_audit.py::rel` | `scripts/primitive_family_readiness_ledger.py::relpath` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/primitive_duplication_audit.py::rel` | `scripts/primitive_readiness_ledger.py::relpath` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/primitive_family_readiness_ledger.py::family_counts` | `scripts/primitive_readiness_ledger.py::family_counts` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/primitive_family_readiness_ledger.py::load_lifecycle` | `scripts/primitive_readiness_ledger.py::load_lifecycle` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/primitive_family_readiness_ledger.py::row_to_dict` | `scripts/primitive_readiness_ledger.py::row_to_dict` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | 1.0 | `scripts/primitive_surface_reduce.py::load_json` | `scripts/reduction_backlog.py::load_json` | extract-common-python-helper | `lib/` | so-local-first |

## Interpretation

- Treat findings as refactor candidates, not automatic rewrite instructions.
- Keep intentional duplication only when isolation, portability, or harness-specific behavior is documented.
- Promote repeated projected primitive behavior into shared rules/skills/hooks only after ACC projection proof exists.
