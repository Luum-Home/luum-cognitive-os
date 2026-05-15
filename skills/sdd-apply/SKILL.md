---
name: sdd-apply
command: /sdd-apply
description: Implement SDD tasks against requirements and EAS acceptance rows.
trigger: Orchestrator has approved tasks and needs implementation.
inputs:
- change-name: Stable SDD change name.
- tasks: Task list from sdd-tasks.
- eas: Executable Acceptance Specification path when present.
outputs:
- implementation: Files changed and evidence collected.
- apply-progress: Completed tasks and remaining gaps.
version: 1.0.0
audience: project
platforms:
- claude-code
- codex
routing_patterns:
- pattern: \bsdd[- ]?apply\b
  confidence: 0.96
- pattern: \bimplement against EAS\b
  confidence: 0.88
triggers:
- sdd-apply
- /sdd-apply
- EAS implementation
---
<!-- SCOPE: both -->
# SDD Apply

## Purpose

Implement the approved task list while preserving traceability from code changes to EAS requirements, EARS trigger/response wording, acceptance criteria, and detractor objections.

## EAS Implementation Rule

When EAS exists, do not treat prose completion as enough. For every implemented task, record which `REQ-*`, `AC-*`, and `OBJ-*` rows it addresses and what evidence will prove it.

## Procedure

1. Read tasks and EAS before editing.
2. Implement tasks in dependency order.
3. Add or update tests that satisfy the ATDD/TDD mapping where applicable.
4. Update implementation evidence for each completed EAS row in the apply progress report.
5. If implementation reveals a new gap, update the EAS gap matrix or report the exact required EAS change to the orchestrator.
6. Do not mark an EAS-linked task complete unless its expected verification command or manual evidence is identified.

## Output Contract

```text
SDD_APPLY: <change-name>
EAS path: <path or none>
Completed tasks: <count>
Completed EAS rows: <REQ/AC/OBJ list>
Remaining EAS gaps: <count>
Verification evidence prepared: <commands/manual checks>
```

`SDD_APPLY` hands off to `sdd-verify`, which must run `scripts/eas_validate.py` and the listed verification commands.
