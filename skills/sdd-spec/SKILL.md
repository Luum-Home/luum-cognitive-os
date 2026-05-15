---
name: sdd-spec
command: /sdd-spec
description: Use when creating or updating the SDD specification and emitting an Executable Acceptance Specification with EARS-style functional requirements when requested or risk warrants it.
trigger: Orchestrator needs a requirements/specification phase for a medium, large, critical, EARS-requested, or EAS-requested change.
inputs:
- change-name: Stable SDD change name.
- proposal: Prior proposal or exploration context.
- eas-requested: Whether the user or project policy requested EAS.
outputs:
- spec: Requirements and non-goals for the change.
- eas: Executable Acceptance Specification when required.
version: 1.0.0
audience: project
platforms:
- claude-code
- codex
routing_patterns:
- pattern: \bsdd[- ]?spec\b
  confidence: 0.96
- pattern: \bExecutable Acceptance Specification\b
  confidence: 0.9
- pattern: \bEARS\b
  confidence: 0.9
- pattern: \bEasy Approach to Requirements Syntax\b
  confidence: 0.9
triggers:
- sdd-spec
- /sdd-spec
- EAS specification
- EARS requirements
---
<!-- SCOPE: both -->
# SDD Spec

## Purpose

Translate proposal context into EARS-style functional requirements, non-goals, and executable acceptance criteria. When EAS is requested or the change is large/critical, create or update an EAS artifact from `templates/eas.md`.

## EAS Emission Rule

Emit EAS when any condition is true:

- the user asks for EAS, EARS, Easy Approach to Requirements Syntax, Executable Acceptance Specification, SDD Evidence Artifact, gap matrix, or detractor log;
- the user asks for Tenth Man Rule, Devil's Advocate, Pre-mortem, Black Hat, Red Team, or a required contrary thesis;
- the change is large, critical, security-sensitive, migration-related, or cross-service;
- acceptance criteria need ATDD/TDD mapping;
- multiple documentation sources must be reconciled.

## Procedure

1. Gather proposal, exploration, existing docs, contracts, tests, and constraints.
2. Write requirements as stable `REQ-*` rows. Functional rows should use EARS patterns: `WHEN ... THE SYSTEM SHALL ...`, `IF ... THEN THE SYSTEM SHALL ...`, `WHILE ... THE SYSTEM SHALL ...`, `WHERE ... THE SYSTEM SHALL ...`, or `THE SYSTEM SHALL ...`.
3. Write non-goals to bound scope.
4. Convert every requirement into at least one `AC-*` executable acceptance row with verification method and expected result; each acceptance row must prove the observable EARS response, not merely restate prose.
5. Create the EAS artifact using `templates/eas.md` when the EAS emission rule applies.
6. Populate the initial gap matrix. Rows may start as uncovered only before implementation; do not mark an EAS complete while uncovered rows remain.
7. Add adversarial personas, including `Detractor`.
8. Select one or more detractor modes: Tenth Man Rule, Devil's Advocate, Pre-mortem, Black Hat, or Red Team.
9. Add at least one substantive `OBJ-*` detractor objection, contrary thesis, and required evidence.
10. Add verification commands or manual checks that `sdd-verify` can execute or inspect.
11. Save the spec and EAS path in the phase output.

## Output Contract

Return:

```text
SDD_SPEC: <change-name>
Spec path: <path or Engram topic>
EAS path: <path or none with reason>
Requirements: <count>
Acceptance criteria: <count>
Open gaps: <count>
Detractor objections: <count>
Detractor modes: <modes>
Verification commands: <count>
```

## Handoff To sdd-tasks

If EAS exists, `sdd-tasks` must consume the EAS gap matrix and ATDD/TDD mapping. Include the EAS path in the handoff.
