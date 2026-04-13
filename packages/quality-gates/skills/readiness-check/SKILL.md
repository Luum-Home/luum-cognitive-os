---
name: readiness-check
command: /readiness-check
description: Implementation readiness gate — validates all prerequisites before coding starts
trigger: Before sdd-apply, or manually via /readiness-check
inputs:
  - change-name (optional): SDD change to check. If omitted, checks general readiness.
outputs:
  - verdict: PASS | CONCERNS | FAIL
  - checklist: detailed results per check
  - blockers: list of items that must be fixed before implementing
audience: project
---

# Implementation Readiness Check

## Purpose

Gate between planning and implementation. Ensures all prerequisites are met before writing code. This prevents wasted implementation effort on incomplete plans.

## When to Run

- **Automatic**: Orchestrator runs this BEFORE launching `sdd-apply`
- **Manual**: User invokes `/readiness-check [change-name]`
- **On demand**: Any agent can request a readiness check before starting implementation

## Checklist

The readiness check evaluates these dimensions:

### 1. Specs Complete
- [ ] Spec artifact exists in engram (`sdd/{change-name}/spec`)
- [ ] Spec contains: scope, requirements, acceptance criteria
- [ ] Spec has been reviewed (adversarial review produced findings, all BLOCKERs resolved)

### 2. Design Reviewed
- [ ] Design artifact exists in engram (`sdd/{change-name}/design`)
- [ ] Design specifies: components, interfaces, data flow
- [ ] Design follows architecture standards from `cognitive-os.yaml -> project.architecture.evaluation_criteria`
- [ ] Design uses the correct framework per language from `cognitive-os.yaml -> project.architecture.frameworks`
- [ ] Design addresses cross-service communication via SDKs (not direct imports)

### 3. Tasks Broken Down
- [ ] Tasks artifact exists in engram (`sdd/{change-name}/tasks`)
- [ ] Each task has: description, affected files, estimated complexity
- [ ] Tasks are ordered by dependency (no circular dependencies)
- [ ] No single task spans more than 3 files (break it down further)

### 4. Dependencies Identified
- [ ] All required services are listed
- [ ] Inter-service communication paths are documented
- [ ] Required infrastructure (DB, queue, cache) is identified
- [ ] No dependency on unavailable external services without mocks

### 5. Mock Providers Configured
- [ ] All external providers have mock implementations
- [ ] Mock flags are documented in env configuration
- [ ] Mocks return realistic data structures
- [ ] Constitutional Gate 2 (Mock Before Integrate) is satisfied

### 6. Tests Planned
- [ ] Test strategy defined (unit, integration, e2e)
- [ ] Critical paths identified for test coverage
- [ ] Test data / fixtures identified or planned
- [ ] Coverage target set (from `cognitive-os.yaml -> quality.coverage.minimum`, default 80%)

## Execution Steps

1. **Read project config**: Load `cognitive-os.yaml` to get `project.architecture` (frameworks, layers, evaluation_criteria) and `quality.coverage.minimum`. These drive all architecture checks below instead of hardcoded framework names.
2. **Retrieve artifacts**: Search engram for spec, design, and tasks using topic keys
3. **Validate each dimension**: Check existence and completeness
4. **Score results**: Each dimension is GREEN (complete), YELLOW (partial), or RED (missing/incomplete)
5. **Determine verdict**:
   - **PASS**: All dimensions GREEN
   - **CONCERNS**: No RED, but some YELLOW. Proceed with caution, note what's incomplete.
   - **FAIL**: Any dimension RED. Must fix before implementing.
6. **Return structured result**

## Result Format

```yaml
verdict: PASS | CONCERNS | FAIL
change: {change-name}
checks:
  specs_complete:
    status: GREEN | YELLOW | RED
    detail: "..."
  design_reviewed:
    status: GREEN | YELLOW | RED
    detail: "..."
  tasks_broken_down:
    status: GREEN | YELLOW | RED
    detail: "..."
  dependencies_identified:
    status: GREEN | YELLOW | RED
    detail: "..."
  mock_providers:
    status: GREEN | YELLOW | RED
    detail: "..."
  tests_planned:
    status: GREEN | YELLOW | RED
    detail: "..."
blockers:
  - "{description of what must be fixed}"
concerns:
  - "{description of what should be addressed}"
recommendation: "Proceed" | "Fix blockers first" | "Address concerns, then proceed"
```

## SDD Integration

This skill acts as a GATE in the SDD dependency graph:

```
proposal -> specs --> tasks -> [READINESS CHECK] -> apply -> verify -> archive
             ^
             |
           design
```

The orchestrator MUST run `/readiness-check` before launching `sdd-apply`. If the verdict is FAIL, the orchestrator MUST NOT proceed to apply and instead reports blockers to the user.

## Standalone Usage

When invoked without a change-name, the skill checks general project readiness:
- Are there pending architecture violations?
- Is the local stack healthy?
- Are there unresolved BLOCKERs from previous reviews?
- Is the test suite passing?
