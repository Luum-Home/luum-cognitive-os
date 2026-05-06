# Confidentiality Enforcer Gitignored-Destination Downgrade — 2026-05-06

## Problem

The confidentiality enforcer correctly protects against developer/operator absolute paths leaking into generated documentation, but it was blocking writes to gitignored local scratch/session artifacts. That created a dogfood false positive: local, non-committable notes could not mention operator paths even when the content was never meant to enter version control.

## Decision

Do **not** disable confidentiality enforcement for gitignored files globally. A gitignored artifact can still be exported or copied by another workflow.

Apply a narrow downgrade only when all conditions are true:

```text
finding type == external_path / operator absolute path
and destination path is gitignored by the project
and tool is Write or Edit
then downgrade BLOCK -> WARN
```

Any mixed or stronger confidentiality violation still blocks, including protected terms, attribution phrases, repository URLs, and operator absolute paths in tracked/committable docs.

## Implemented behavior

| Scenario | Result |
|---|---|
| Gitignored markdown with only `/Users/<operator>/Projects/<external>` path | WARN, exit 0 |
| Gitignored markdown with protected term such as `project-x` | BLOCK, exit 2 |
| Tracked/committable markdown with operator absolute path | BLOCK, exit 2 |
| Source code files | Existing skip behavior preserved |

## Why this boundary is safe

The downgrade removes local-session friction without changing the public/confidentiality boundary. The hook still emits a warning and metrics row with `downgrade_reason=operator_absolute_path_gitignored_destination`, preserving observability for future ADR-201/204 analysis.

## Validation

```bash
python3 -m pytest tests/behavior/test_confidentiality_enforcer.py -q
bash -n hooks/confidentiality-enforcer.sh
```
