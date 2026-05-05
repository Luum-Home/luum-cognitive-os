# Primitive Duplication Audit — Latest

Generated: `2026-05-05T18:12:48.966099+00:00`

## Summary

- Files scanned: 774
- Findings: 5
- By kind: `{"python-function-repeat": 5}`
- By common home: `{"lib/": 5}`
- By consumer relevance: `{"so-local-first": 5}`

## Top Candidates

| Kind | Classification | Similarity | Left | Right | Recommendation | Common home | Consumer relevance |
|---|---|---:|---|---|---|---|---|
| python-function-repeat | candidate | 1.0 | `scripts/acc_pipeline.py::utc_now` | `scripts/proof_drill_evidence_record.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_credential_safe_run.py::_load_manifest` | `scripts/security_red_team.py::_read_yaml` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_credential_safe_run.py::_sha256_file` | `scripts/security_red_team.py::_file_sha256` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_credential_safe_run.py::_utc` | `scripts/security_red_team.py::_utc` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/project_shell_ci.py::load_manifest` | `scripts/proof_drill_select.py::load_registry` | extract-common-python-helper | `lib/` | so-local-first |

## Interpretation

- Treat findings as refactor candidates, not automatic rewrite instructions.
- Keep intentional duplication only when isolation, portability, or harness-specific behavior is documented.
- Promote repeated projected primitive behavior into shared rules/skills/hooks only after ACC projection proof exists.
