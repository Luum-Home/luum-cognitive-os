---
adr: 317
title: Executable Acceptance Specification (EAS) Evidence Artifact
status: accepted
implementation_status: partial
date: '2026-05-15'
supersedes: []
superseded_by: null
implementation_files:
- docs/05-Methodology/root/executable-acceptance-specification.md
- templates/eas.md
- rules/eas-evidence-artifact.md
- scripts/eas_validate.py
- skills/sdd-spec/SKILL.md
- skills/sdd-tasks/SKILL.md
- skills/sdd-apply/SKILL.md
- skills/sdd-verify/SKILL.md
tier: product
classification_basis: accepted doctrine, template, rule, validator, and SDD skill wiring; runtime orchestration still depends on harness/skill invocation
partial_remaining: EAS validation and skill guidance exist, but there is no automatic hook that forces every SDD run to create EAS unless the user or project policy requests it.
remaining_in_scope: true
---

# ADR-317: Executable Acceptance Specification (EAS) Evidence Artifact

## Context

Cognitive OS already had distributed evidence practices: mandatory acceptance criteria, verification commands, SDD phases, adversarial review with zero-finding halt, gap matrices in audit work, and residual-risk sections in several ADRs.

The missing doctrine was a single optional developer-facing artifact that turns intention into acceptance evidence without forcing teams to abandon their existing documentation formats.

## Decision

Adopt **Executable Acceptance Specification (EAS)** as an optional documentation artifact for significant changes.

EAS is not a replacement for SDD:

```text
SDD = workflow / process
EAS = artifact / documentation format
ATDD/TDD = execution and verification style
```

EAS must be able to represent or reference other known formats while preserving executable acceptance as the invariant. Its canonical sections are: Intent, Requirements, Non-goals, Executable acceptance criteria, Gap matrix, Adversarial personas, Detractor objection log, Verification commands, and Residual risks. Functional requirements inside EAS should use EARS (Easy Approach to Requirements Syntax) patterns when the behavior can be stated that way.

EAS is mandatory only when a caller, skill, or project policy asks for it. Otherwise it is recommended for large or critical SDD work and optional for smaller changes.

## Relationship to Existing Formats

EAS is an adapter layer, not a competing methodology.

| Existing format | EAS relationship |
|---|---|
| PRD | Product intent, users, goals, non-goals, and success measures. |
| RFC | Alternatives, tradeoffs, open questions, and proposed approach. |
| ADR | Durable decisions and consequences. |
| EARS | Preferred syntax for functional requirement statements inside the Requirements section. EARS means Easy Approach to Requirements Syntax and uses patterns such as `WHEN ... THE SYSTEM SHALL ...`, `IF ... THEN THE SYSTEM SHALL ...`, `WHILE ... THE SYSTEM SHALL ...`, and `WHERE ... THE SYSTEM SHALL ...`. |
| Gherkin | Executable behavior scenarios for ATDD. |
| OpenAPI / AsyncAPI | External API contracts and contract tests. |
| Test plan | Manual, unit, integration, contract, and regression checks. |
| Threat model | Abuse cases, security requirements, and mitigations. |
| Runbook | Rollout, rollback, observability, and operational checks. |

## Integration with SDD

Full SDD can emit and consume EAS as follows:

```text
explore -> propose -> spec/design -> EAS -> tasks -> apply -> verify -> archive
```

- `sdd-spec` creates or updates EAS requirements and executable acceptance sections when EAS is requested or risk warrants it.
- `sdd-tasks` derives implementation tasks from the EAS gap matrix and acceptance mapping.
- `sdd-apply` implements against EAS acceptance rows, not only prose requirements.
- `sdd-verify` runs `scripts/eas_validate.py` and checks that every EAS requirement has evidence, every unresolved gap is explicit, and every detractor objection is either addressed or carried as residual risk.

The Detractor mode taxonomy itself is owned by ADR-319. ADR-317 owns the EAS artifact and its validator-backed implementation surface. EARS is deliberately not renamed to EAS: EARS is the requirement syntax; EAS is the evidence artifact that can contain EARS-formatted requirements.

## Adversarial Review Requirement

EAS introduces a stronger adversarial shape than generic review: adversarial personas review from distinct stakeholder lenses; a named **Detractor** argues that the implementation will fail to satisfy the artifact; objections are logged before implementation or before final verification; and every objection is resolved by evidence, converted into a task, or accepted as residual risk.

For mode selection, EAS follows ADR-319: `Detractor` is the slot, while Tenth Man Rule, Devil's Advocate, Pre-mortem, Black Hat, and Red Team are selectable modes.

## Consequences

Positive: SDD gains a single evidence artifact that can bridge documentation, ATDD, and TDD; acceptance criteria become traceable from requirement to test/evidence; existing formats remain usable; and adversarial review becomes part of the specification, not only a late verify step.

Tradeoffs: EAS adds ceremony when used on trivial or small changes. Runtime validation now exists, but automatic enforcement still depends on whether the orchestrator or project policy invokes EAS for a given change.

## Verification

```bash
test -f docs/05-Methodology/root/executable-acceptance-specification.md
test -f templates/eas.md
test -f rules/eas-evidence-artifact.md
test -f scripts/eas_validate.py
.venv/bin/python -m pytest tests/contracts/test_eas_docs_contract.py tests/contracts/test_eas_manifest_and_sdd_wiring.py tests/unit/test_eas_validate.py -q
```
