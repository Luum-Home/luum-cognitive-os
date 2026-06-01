# Primitive Duplication Audit — Latest

Generated: `2026-06-01T00:22:56.941367+00:00`

## Summary

- Files scanned: 777
- Findings: 134
- By kind: `{"python-function-repeat": 134}`
- By common home: `{"lib/": 134}`
- By consumer relevance: `{"so-local-first": 134}`
- Ratchet status: `pass`
- Baseline findings: 134
- New findings: 0

## Top Candidates

| Kind | Classification | Similarity | Left | Right | Recommendation | Common home | Consumer relevance |
|---|---|---:|---|---|---|---|---|
| python-function-repeat | candidate | 1.0 | `lib/adaptive_profile.py::_now_iso` | `lib/dynamic_tool_creator.py::_timestamp` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/adaptive_profile.py::_now_iso` | `lib/engram_claims.py::_now_iso` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/adaptive_profile.py::_now_iso` | `lib/engram_locks.py::_now_iso` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/adaptive_profile.py::_now_iso` | `lib/engram_write_gate.py::_now_iso` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/adaptive_profile.py::_now_iso` | `lib/hook_tuner.py::_now_iso` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/adaptive_profile.py::_now_iso` | `lib/learning_pipeline.py::_now_iso` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/adaptive_profile.py::_now_iso` | `lib/skill_store.py::_now_iso` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/adaptive_profile.py::_now_iso` | `scripts/cos_promotion_proposer.py::_now_iso` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/adaptive_profile.py::_now_iso` | `scripts/migrate_skill_archive_to_store.py::_now_iso` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/adaptive_profile.py::git` | `lib/operational_status.py::git` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/adaptive_profile.py::git` | `scripts/cos_coordination_status.py::run` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/adversarial_rubric.py::_write` | `scripts/run_skill_lifecycle_promotion_smoke.py::_write` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/agent_bus_metrics.py::_as_float` | `lib/dispatch_gate.py::_as_float` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/agent_bus_metrics.py::_as_float` | `lib/outcome_metrics.py::_as_float` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/agent_bus_metrics.py::_project_root` | `lib/process_registry.py::_project_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/agent_bus_metrics.py::_project_root` | `lib/targeted_test_resolver.py::_project_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/agent_control_policy.py::_read_json` | `lib/intent_arbiter.py::read_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/agent_daemon.py::_append_jsonl` | `lib/agent_team.py::_append_jsonl` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/agent_health_monitor.py::_now_utc` | `lib/taximeter.py::_now_utc` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/agent_health_monitor.py::_now_utc` | `scripts/adr_reserve.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/agent_message_bus.py::_append_jsonl` | `scripts/context_budget_meter_fast.py::_append` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/agent_message_bus.py::_read_rows` | `lib/friction_telemetry.py::load_jsonl` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/agent_message_bus.py::current_session` | `lib/session_bus.py::_session_id` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/agent_message_bus.py::current_session` | `scripts/cos_task_claims.py::session_id` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/agent_trajectory.py::to_dict` | `lib/runtime_benchmark.py::to_dict` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/ai_provider_identity_guard.py::_git` | `lib/release_freeze.py::git` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/bifrost_client.py::__init__` | `lib/cognee_client.py::__init__` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/bifrost_client.py::__init__` | `lib/litellm_client.py::__init__` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/branch_lock.py::_pid_alive` | `lib/intent_arbiter.py::pid_alive` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/branch_lock.py::_pid_alive` | `lib/session_bus.py::_pid_alive` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/concurrent_agent_safety_status.py::_now_iso` | `lib/intent_arbiter.py::utc_now_iso` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/concurrent_agent_safety_status.py::_now_iso` | `scripts/cos_instance_init.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/concurrent_agent_safety_status.py::_read_json_object` | `scripts/resource_lease.py::read_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/consumer_improvement_proposals.py::_utc_now` | `lib/cross_instance_learning.py::_utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/consumer_improvement_proposals.py::_utc_now` | `lib/governed_self_improvement.py::_utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/consumer_improvement_proposals.py::_utc_now` | `lib/key_learning_capture.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/consumer_improvement_proposals.py::_utc_now` | `lib/project_profile_bootstrap.py::_utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/consumer_improvement_proposals.py::_utc_now` | `lib/skill_drift_detector.py::_utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/consumer_improvement_proposals.py::_utc_now` | `scripts/cos_run_task.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/context_budget.py::metrics_path` | `lib/context_budget_monitor.py::metrics_path` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/context_injector.py::_jaccard` | `lib/reinvention_semantic.py::_jaccard` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/cost_dashboard.py::_parse_timestamp` | `lib/cost_predictor.py::_parse_timestamp` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/cross_instance_learning.py::_load_yaml` | `scripts/cos_claim_signature_audit.py::load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/cross_stack_adoption_truth.py::dumps_json` | `lib/cross_stack_license_audit.py::dumps_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/cross_stack_adoption_truth.py::dumps_json` | `lib/cross_stack_secret_audit.py::dumps_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/cross_stack_adoption_truth.py::dumps_json` | `lib/dependency_adoption_gate.py::dumps_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/cross_stack_adoption_truth.py::dumps_json` | `lib/history_sanitization.py::dumps_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/cross_stack_adoption_truth.py::dumps_json` | `lib/tool_discovery_preuse.py::dumps_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/cross_stack_license_audit.py::_run` | `lib/cross_stack_secret_audit.py::_run` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/cross_stack_license_audit.py::_workflow_files` | `lib/cross_stack_secret_audit.py::_workflow_files` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/deferred_tool_loading.py::dumps_json` | `lib/policy_eval.py::dumps_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/dependency_adoption_gate.py::exit_code` | `scripts/subagent_launch_preflight.py::exit_code` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/dependency_adoption_gate.py::repo_root` | `lib/reward_signal_quality.py::repo_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/dependency_adoption_gate.py::repo_root` | `lib/trace_joiner.py::repo_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/dependency_adoption_gate.py::repo_root` | `scripts/private_content_audit.py::repo_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/dependency_adoption_gate.py::repo_root` | `scripts/subagent_launch_preflight.py::repo_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/dependency_coverage_audit.py::_rel` | `lib/dependency_maintenance.py::_relative` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/dependency_coverage_audit.py::dumps_json` | `lib/external_tool_intelligence.py::write_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/dependency_coverage_audit.py::dumps_json` | `lib/feature_tool_due_diligence.py::write_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/dependency_tool_intake.py::load_coverage` | `lib/memory_retrieval_benchmark.py::load_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/dependency_tool_intake.py::load_coverage` | `lib/session_lifecycle.py::_read_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/dependency_tool_intake.py::load_coverage` | `lib/task_reconciliation.py::_read_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/dependency_tool_intake.py::load_coverage` | `scripts/primitive_harness_partials.py::_load_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/dispatch_gate.py::_as_int` | `scripts/primitive_gap_snapshot.py::_as_int` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/engram_bundle_exporter.py::_bundle_sha256` | `lib/engram_bundle_importer.py::_bundle_sha256` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/engram_bundle_exporter.py::_columns` | `lib/engram_bundle_importer.py::_existing_columns` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/engram_bundle_exporter.py::_sha256_file` | `lib/engram_bundle_importer.py::_sha256_file` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/engram_bundle_exporter.py::_table_exists` | `lib/engram_bundle_importer.py::_table_exists` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/engram_wave2_schema.py::observation_columns` | `lib/engram_wave3_schema.py::_observation_columns` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/engram_wave3_schema.py::to_dict` | `lib/routing_benchmark.py::to_dict` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/event_bus.py::_now_iso` | `lib/merge_queue.py::_now_iso` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/external_tool_intelligence.py::_display_path` | `lib/feature_tool_due_diligence.py::display_path` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/external_tool_intelligence.py::_display_path` | `lib/memory_retrieval_benchmark.py::display_path` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/external_tool_intelligence.py::read_yaml` | `lib/feature_tool_due_diligence.py::read_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/external_tool_intelligence.py::read_yaml` | `scripts/agent-orchestration-benchmark.py::load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/external_tool_intelligence.py::read_yaml` | `scripts/agent-orchestration-boundary-audit.py::load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/external_tool_intelligence.py::read_yaml` | `scripts/documentation_truth_audit.py::read_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/external_tool_intelligence.py::read_yaml` | `scripts/primitive-behavior-audit.py::load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/external_tool_intelligence.py::read_yaml` | `scripts/primitive-coherence-audit.py::load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/external_tool_intelligence.py::read_yaml` | `scripts/primitive_authority_audit.py::read_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/external_tool_intelligence.py::read_yaml` | `scripts/primitive_behavior_depth_audit.py::_load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/external_tool_intelligence.py::read_yaml` | `scripts/skill-router-benchmark.py::load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/external_tool_intelligence.py::read_yaml` | `scripts/skill-router-retrieval-audit.py::load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/external_tool_intelligence.py::repo_root` | `lib/feature_tool_due_diligence.py::repo_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/feedback_detector.py::_compile_patterns` | `lib/prompt_classifier.py::_compile_patterns` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/fleet_confidence.py::load_yaml` | `lib/memory_retrieval_benchmark.py::load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/fleet_confidence.py::load_yaml` | `lib/policy_eval.py::_load_policy_file` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/fleet_confidence.py::load_yaml` | `scripts/project_shell_ci.py::load_manifest` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/fleet_confidence.py::load_yaml` | `scripts/proof_drill_select.py::load_registry` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/fleet_confidence.py::load_yaml` | `scripts/self_programming_pattern_audit.py::load_manifest` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/fleet_confidence.py::load_yaml` | `scripts/state_retention_audit.py::load_manifest` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/handoff_dispatcher.py::_project_root` | `lib/session_bus.py::_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/history_rewrite_ledger.py::__init__` | `lib/history_sanitization.py::__init__` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/history_sanitization.py::_upstream_tracking_ref` | `lib/prelaunch_audit.py::upstream_tracking_ref` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/improve_loop.py::utc_stamp` | `lib/prelaunch_audit.py::utc_stamp` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/improve_loop.py::utc_stamp` | `lib/release_freeze.py::compact_ts` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/improve_loop.py::utc_stamp` | `lib/reward_signal_quality.py::utc_stamp` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/improve_loop.py::utc_stamp` | `scripts/cos_cleanup_preserved_wip.py::utc_stamp` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/improve_loop.py::utc_stamp` | `scripts/state_retention_audit.py::stamp` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `lib/install_timing.py::_iso_now` | `lib/phase_timing.py::_iso_now` | extract-common-python-helper | `lib/` | so-local-first |

## Interpretation

- Treat findings as refactor candidates, not automatic rewrite instructions.
- Keep intentional duplication only when isolation, portability, or harness-specific behavior is documented.
- Promote repeated projected primitive behavior into shared rules/skills/hooks only after ACC projection proof exists.
