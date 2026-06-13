# Primitive Duplication Audit — Latest

Generated: `2026-06-13T05:25:51.047043+00:00`

## Summary

- Files scanned: 1031
- Findings: 1
- By kind: `{"python-function-repeat": 1}`
- By common home: `{"lib/": 1}`
- By consumer relevance: `{"so-local-first": 1}`

## Top Candidates

| Kind | Classification | Similarity | Left | Right | Recommendation | Common home | Consumer relevance |
|---|---|---:|---|---|---|---|---|
| python-function-repeat | candidate | 1.0 | `scripts/cos_agent_flicker_report.py::_utc_now` | `scripts/cos_instance_init.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |

## Interpretation

- Treat findings as refactor candidates, not automatic rewrite instructions.
- Keep intentional duplication only when isolation, portability, or harness-specific behavior is documented.
- Promote repeated projected primitive behavior into shared rules/skills/hooks only after ACC projection proof exists.
