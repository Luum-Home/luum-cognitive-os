---
name: sdd-tasks
command: /sdd-tasks
description: Use when converting SDD spec/design/EAS evidence into implementation tasks.
trigger: Orchestrator needs to break a spec, design, or EAS into concrete tasks before implementation.
inputs:
- change-name: Stable SDD change name.
- spec: Specification source.
- design: Design source when present.
- eas: Executable Acceptance Specification path when present.
outputs:
- tasks: Ordered implementation and verification tasks.
version: 1.0.0
audience: project
platforms:
- claude-code
- codex
routing_patterns:
- pattern: \bsdd[- ]?tasks\b
  confidence: 0.96
- pattern: \bEAS gap matrix\b
  confidence: 0.88
triggers:
- sdd-tasks
- /sdd-tasks
- EAS task breakdown
---
<!-- SCOPE: both -->
# SDD Tasks

## Purpose

Convert requirements, design decisions, and EAS coverage gaps into concrete implementation tasks; preserve EARS requirement wording when deriving tasks.

## EAS Consumption Rule

When an EAS path exists, tasks must be derived from:

- each `REQ-*` requirement, preserving any EARS trigger/condition/state/context and `THE SYSTEM SHALL` response;
- each `AC-*` acceptance row;
- every gap-matrix row whose status is not covered;
- every `OBJ-*` detractor objection whose disposition requires a task;
- verification commands that require new tests, fixtures, scripts, docs, or contracts.

## Procedure

1. Read the spec/design and the EAS artifact if present.
2. Run `python3 scripts/eas_validate.py <eas.md>` if the EAS is intended to be complete before implementation; otherwise use validator output to identify planned gaps.
3. Create one or more tasks per uncovered EAS row.
4. Include task IDs that reference EAS IDs, such as `TASK-1 covers REQ-1 / AC-1 / OBJ-1`.
5. Separate implementation tasks from verification tasks.
6. Mark dependencies between tasks so `sdd-apply` can implement in safe order.

## Output Contract

```text
SDD_TASKS: <change-name>
EAS path: <path or none>
Tasks: <count>
EAS-linked tasks: <count>
Verification tasks: <count>
Blocked gaps: <count>
```

Each task must include affected files, EAS IDs covered, expected evidence, and verification command or manual check.
