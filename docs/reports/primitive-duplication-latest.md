# Primitive Duplication Audit — Latest

Generated: `2026-05-05T16:45:05.428762+00:00`

## Summary

- Files scanned: 747
- Findings: 2
- By kind: `{"python-function-repeat": 2}`
- By common home: `{"lib/": 2}`
- By consumer relevance: `{"so-local-first": 2}`

## Top Candidates

| Kind | Classification | Similarity | Left | Right | Recommendation | Common home | Consumer relevance |
|---|---|---:|---|---|---|---|---|
| python-function-repeat | candidate | 1.0 | `scripts/acc_pipeline.py::utc_now` | `scripts/proof_drill_evidence_record.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/project_shell_ci.py::load_manifest` | `scripts/proof_drill_select.py::load_registry` | extract-common-python-helper | `lib/` | so-local-first |

## Interpretation

- Treat findings as refactor candidates, not automatic rewrite instructions.
- Keep intentional duplication only when isolation, portability, or harness-specific behavior is documented.
- Promote repeated projected primitive behavior into shared rules/skills/hooks only after ACC projection proof exists.
