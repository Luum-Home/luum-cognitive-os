---
name: sdd-verify
command: /sdd-verify
description: Verify SDD implementation, including EAS coverage, detractor disposition, and executable evidence.
trigger: Implementation is complete and needs independent verification.
inputs:
- change-name: Stable SDD change name.
- apply-progress: Implementation report.
- eas: Executable Acceptance Specification path when present.
outputs:
- verify-report: Pass/fail report with findings and evidence.
version: 1.0.0
audience: project
platforms:
- claude-code
- codex
routing_patterns:
- pattern: \bsdd[- ]?verify\b
  confidence: 0.96
- pattern: \bverify EAS\b
  confidence: 0.9
triggers:
- sdd-verify
- /sdd-verify
- EAS verification
---
<!-- SCOPE: both -->
# SDD Verify

## Purpose

Independently verify implementation against SDD requirements and EAS executable evidence.

## EAS Verification Rule

When EAS exists, verification must run:

```bash
python3 scripts/eas_validate.py <eas.md>
```

Verification fails if the validator fails, unless the user explicitly accepts a partial EAS and the verify report records each residual risk.

## Procedure

1. Read apply-progress and EAS.
2. Apply `rules/adversarial-review.md`: produce at least one finding and classify severity.
3. Run `python3 scripts/eas_validate.py <eas.md>` when EAS exists.
4. Execute verification commands listed in EAS or mark manual checks with evidence.
5. Confirm every `REQ-*` is covered by `AC-*` and evidence.
6. Confirm at least one detractor mode is named when EAS exists: Tenth Man Rule, Devil's Advocate, Pre-mortem, Black Hat, or Red Team.
7. Confirm every `OBJ-*` detractor objection is resolved, converted into a task, or carried as residual risk.
8. Confirm residual risks are explicit, bounded, and acceptable for the current project phase.
9. Return PASS only when validation and verification evidence support it.

## Output Contract

```text
SDD_VERIFY: <change-name>
Verdict: PASS | FAIL | PARTIAL
EAS validation: PASS | FAIL | NOT_USED
Verification commands run: <count>
Findings: <count>
Residual risks: <count>
Required follow-up: <items>
```
