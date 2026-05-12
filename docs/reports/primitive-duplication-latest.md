# Primitive Duplication Audit — Latest

Generated: `2026-05-12T17:47:07.364672+00:00`

## Summary

- Files scanned: 962
- Findings: 29
- By kind: `{"python-function-repeat": 29}`
- By common home: `{"lib/": 29}`
- By consumer relevance: `{"so-local-first": 29}`

## Top Candidates

| Kind | Classification | Similarity | Left | Right | Recommendation | Common home | Consumer relevance |
|---|---|---:|---|---|---|---|---|
| python-function-repeat | candidate | 1.0 | `scripts/acc_pipeline.py::utc_now` | `scripts/proof_drill_evidence_record.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/agent-orchestration-benchmark.py::load_yaml` | `scripts/agent-orchestration-boundary-audit.py::load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/agent-orchestration-benchmark.py::load_yaml` | `scripts/documentation_truth_audit.py::read_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/agent-orchestration-benchmark.py::load_yaml` | `scripts/primitive-behavior-audit.py::load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/agent-orchestration-benchmark.py::load_yaml` | `scripts/primitive-coherence-audit.py::load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/agent-orchestration-benchmark.py::load_yaml` | `scripts/primitive_authority_audit.py::read_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/agent-orchestration-benchmark.py::load_yaml` | `scripts/skill-router-benchmark.py::load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/agent-orchestration-benchmark.py::load_yaml` | `scripts/skill-router-retrieval-audit.py::load_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/agent-orchestration-benchmark.py::repo_root` | `scripts/agent-orchestration-boundary-audit.py::repo_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/agent-orchestration-benchmark.py::repo_root` | `scripts/primitive-behavior-audit.py::repo_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/agent-orchestration-benchmark.py::repo_root` | `scripts/skill-router-benchmark.py::repo_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/agent-orchestration-benchmark.py::repo_root` | `scripts/skill-router-retrieval-audit.py::repo_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/agent-orchestration-boundary-audit.py::imported_roots` | `scripts/skill-router-retrieval-audit.py::imported_roots` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos-closure-trust-signal.py::_resolve_project_dir` | `scripts/cos-doc-cross-reference-audit.py::_resolve_project_dir` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos-closure-trust-signal.py::_resolve_project_dir` | `scripts/cos-operational-guide-audit.py::_resolve_project_dir` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos-closure-trust-signal.py::_resolve_project_dir` | `scripts/cos-subprocess-timeout-audit.py::_resolve_project_dir` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_agent_message.py::emit` | `scripts/cos_session_coordination.py::emit` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_cleanup_preserved_wip.py::utc_stamp` | `scripts/state_retention_audit.py::stamp` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_credential_safe_run.py::_load_manifest` | `scripts/security_red_team.py::_read_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_credential_safe_run.py::_sha256_file` | `scripts/security_red_team.py::_file_sha256` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_credential_safe_run.py::_utc` | `scripts/security_red_team.py::_utc` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_promotion_proposer.py::_now_iso` | `scripts/migrate_skill_archive_to_store.py::_now_iso` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_task_claims.py::read_json` | `scripts/state_retention_audit.py::read_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/documentation_truth_audit.py::read_json` | `scripts/primitive_authority_audit.py::read_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/documentation_truth_audit.py::rel` | `scripts/primitive_authority_audit.py::rel` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/private_content_audit.py::repo_root` | `scripts/subagent_launch_preflight.py::repo_root` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/project_shell_ci.py::load_manifest` | `scripts/proof_drill_select.py::load_registry` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/project_shell_ci.py::load_manifest` | `scripts/self_programming_pattern_audit.py::load_manifest` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/project_shell_ci.py::load_manifest` | `scripts/state_retention_audit.py::load_manifest` | extract-common-python-helper | `lib/` | so-local-first |

## Interpretation

- Treat findings as refactor candidates, not automatic rewrite instructions.
- Keep intentional duplication only when isolation, portability, or harness-specific behavior is documented.
- Promote repeated projected primitive behavior into shared rules/skills/hooks only after ACC projection proof exists.
