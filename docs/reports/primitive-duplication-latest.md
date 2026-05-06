# Primitive Duplication Audit — Latest

Generated: `2026-05-06T08:19:39.162979+00:00`

## Summary

- Files scanned: 816
- Findings: 7
- By kind: `{"python-function-repeat": 7}`
- By common home: `{"lib/": 7}`
- By consumer relevance: `{"so-local-first": 7}`

## Top Candidates

| Kind | Classification | Similarity | Left | Right | Recommendation | Common home | Consumer relevance |
|---|---|---:|---|---|---|---|---|
| python-function-repeat | candidate | 1.0 | `scripts/acc_pipeline.py::utc_now` | `scripts/proof_drill_evidence_record.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_agent_message.py::emit` | `scripts/cos_session_coordination.py::emit` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_credential_safe_run.py::_load_manifest` | `scripts/security_red_team.py::_read_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_credential_safe_run.py::_sha256_file` | `scripts/security_red_team.py::_file_sha256` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_credential_safe_run.py::_utc` | `scripts/security_red_team.py::_utc` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_promotion_proposer.py::_now_iso` | `scripts/migrate_skill_archive_to_store.py::_now_iso` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/project_shell_ci.py::load_manifest` | `scripts/proof_drill_select.py::load_registry` | extract-common-python-helper | `lib/` | so-local-first |

## Interpretation

- Treat findings as refactor candidates, not automatic rewrite instructions.
- Keep intentional duplication only when isolation, portability, or harness-specific behavior is documented.
- Promote repeated projected primitive behavior into shared rules/skills/hooks only after ACC projection proof exists.
