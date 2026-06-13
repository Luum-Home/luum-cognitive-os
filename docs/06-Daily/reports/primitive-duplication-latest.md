# Primitive Duplication Audit — Latest

Generated: `2026-06-13T05:49:31.411856+00:00`

## Summary

- Files scanned: 1032
- Findings: 5
- By kind: `{"python-function-repeat": 5}`
- By common home: `{"lib/": 5}`
- By consumer relevance: `{"so-local-first": 5}`

## Top Candidates

| Kind | Classification | Similarity | Left | Right | Recommendation | Common home | Consumer relevance |
|---|---|---:|---|---|---|---|---|
| python-function-repeat | candidate | 1.0 | `scripts/cos_agent_flicker_report.py::_utc_now` | `scripts/cos_instance_init.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_loop.py::load_json` | `scripts/cos_process_loop.py::load_json` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_loop.py::load_jsonl` | `scripts/cos_process_loop.py::load_jsonl` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_loop.py::main` | `scripts/cos_process_loop.py::main` | extract-common-python-helper | `lib/` | so-local-first |
| python-function-repeat | candidate | 1.0 | `scripts/cos_loop.py::utc_now` | `scripts/cos_process_loop.py::utc_now` | extract-common-python-helper | `lib/` | so-local-first |

## Interpretation

- Treat findings as refactor candidates, not automatic rewrite instructions.
- Keep intentional duplication only when isolation, portability, or harness-specific behavior is documented.
- Promote repeated projected primitive behavior into shared rules/skills/hooks only after ACC projection proof exists.
