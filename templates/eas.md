<!-- SCOPE: both -->
# EAS: <change-name>

## Metadata

| Field | Value |
|---|---|
| Status | Draft |
| Owner | <owner> |
| Related SDD change | <planning/change-name> |
| Source documents | <PRD/RFC/ADR/OpenAPI/Gherkin/test plan/threat model/runbook links> |

## Intent

Describe the problem, desired outcome, affected users/operators, and why this change matters now.

## Requirements

| ID | Requirement | Type | Source | Priority |
|---|---|---|---|---|
| REQ-1 | <requirement> | functional | <source> | must |

## Non-goals

- <explicitly out-of-scope behavior or deliverable>

## Executable Acceptance Criteria

| ID | Requirement | Acceptance criterion | Verification method | Expected result |
|---|---|---|---|---|
| AC-1 | REQ-1 | <measurable condition> | <test/command/manual check> | <expected output or pass condition> |

## ATDD/TDD Mapping

| Acceptance criterion | Test style | Test file or scenario | Status |
|---|---|---|---|
| AC-1 | ATDD/TDD/contract/manual | <path or scenario name> | planned |

## Gap Matrix

| Requirement | Acceptance coverage | Evidence | Gap status | Next action |
|---|---|---|---|---|
| REQ-1 | AC-1 | <command/test/report> | covered | <action> |

## Adversarial Personas

| Persona | Lens | Required finding or question |
|---|---|---|
| Product/user | User outcome and missed cases | <finding/question> |
| Maintainer | Maintainability and repo conventions | <finding/question> |
| Security | Abuse, authorization, data handling | <finding/question> |
| Operator/SRE | Rollout, rollback, observability | <finding/question> |
| QA/test | Coverage and reproducibility | <finding/question> |
| Architecture | Boundaries and dependency direction | <finding/question> |
| Detractor | Argues the EAS will fail | <objection> |

## Detractor Objection Log

| ID | Objection | Risk | Required evidence | Disposition |
|---|---|---|---|---|
| OBJ-1 | <why this may fail> | <impact> | <evidence needed> | resolved/task/residual risk |

## Verification Commands

```bash
<command>  # expected: <result>
```

## Residual Risks

| Risk | Why it remains | Owner | Follow-up trigger |
|---|---|---|---|
| <risk or none> | <reason> | <owner> | <event/date/metric> |
