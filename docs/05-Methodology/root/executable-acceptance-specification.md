# Executable Acceptance Specification (EAS)

Executable Acceptance Specification (EAS) is an optional documentation artifact for turning product intent, technical decisions, and acceptance expectations into executable evidence. It is best used for large, critical, ambiguous, or cross-team changes.

## Positioning

```text
SDD = workflow / process
EAS = artifact / documentation format
ATDD/TDD = execution and verification style
```

- **SDD** decides when the agent should explore, propose, specify, design, task, apply, verify, and archive.
- **EAS** records what must be true and how that truth will be proven.
- **EARS** is the preferred syntax for functional requirements inside EAS. It means Easy Approach to Requirements Syntax.
- **ATDD/TDD** turns EAS acceptance rows into behavior tests, unit tests, contract tests, and regression checks.

## Why EAS Exists

Cognitive OS already requires acceptance criteria and verification commands, but significant work needs a stronger bridge between prose requirements and tests. EAS provides that bridge by requiring explicit intent, EARS-friendly requirements and non-goals, executable acceptance criteria, a gap matrix, adversarial personas, a detractor objection log, verification commands, and residual risks.

## Required Sections

### 1. Intent

State the problem, desired outcome, affected users or operators, and why the change matters now.

### 2. Requirements

List functional, non-functional, operational, security, and compatibility requirements. Requirements should be stable enough to map to evidence. Functional requirements should use EARS when possible: event-driven `WHEN <event> THE SYSTEM SHALL <response>`, conditional `IF <condition> THEN THE SYSTEM SHALL <response>`, continuous `WHILE <state> THE SYSTEM SHALL <response>`, optional/feature-scoped `WHERE <feature/context> THE SYSTEM SHALL <response>`, or ubiquitous `THE SYSTEM SHALL <response>`.

### 3. Non-goals

State what the change will not do. Non-goals prevent accidental scope expansion and give the verifier a boundary for rejecting unrelated work.

### 4. Executable Acceptance Criteria

Every acceptance criterion must be measurable and verifiable. Prefer commands or test identifiers over subjective claims.

### 5. Gap Matrix

The gap matrix is the anti-theater section. Every requirement must map to at least one evidence source or an explicit gap.

| Requirement | Acceptance criterion | Evidence | Gap status |
|---|---|---|---|
| REQ-1 | AC-1 | `python3 -m pytest ...` | Covered |
| REQ-2 | AC-4 | Manual review | Partially covered |

### 6. Adversarial Personas

Select personas that can expose different failure modes. A typical set is product/user representative, maintainer, security reviewer, operator/SRE, QA/test reviewer, architecture reviewer, and detractor. The exact count is not mandatory; at least one persona must be structurally skeptical rather than supportive.

### 7. Detractor Mode

The detractor is a **Tenth-Man / Devil's-Advocate-inspired reviewer**: before implementation or final verification, it must argue that the EAS, plan, or implementation will fail. The role is mandatory for EAS and portable to adopter projects because every project can suffer consensus traps, optimistic plans, and late discovery of missing evidence.

Use the lightest mode that matches the risk:

| Mode | Use when | Expected output |
|---|---|---|
| Tenth Man Rule | The team or agent chain has converged on one plan too quickly. | A contrary thesis that assumes the consensus is wrong and names disconfirming evidence. |
| Devil's Advocate | Any medium or larger plan needs skeptical questioning. | Alternatives, drawbacks, weak evidence, and hidden assumptions. |
| Pre-mortem | Rollout, migration, release, or architecture work could fail after approval. | A failure narrative and the most likely causes to prevent. |
| Black Hat | A Six Thinking Hats style review is useful. | Risks, difficulties, and reasons the proposal may not work. |
| Red Team | Security, abuse, prompt-injection, or adversarial misuse is in scope. | Attack paths, exploit hypotheses, and required mitigations. |

The detractor is not a veto by default; it is a structured obligation to make the contrary case before the system claims confidence.

### 8. Detractor Objection Log

Each objection must be resolved by evidence, turned into a task, or carried as residual risk.

| Objection | Risk | Required evidence | Disposition |
|---|---|---|---|
| The migration misses legacy callers. | Partial rollout failure. | Caller count and regression test. | Converted to AC-3. |

### 9. Verification Commands

List the exact commands or manual checks that prove the EAS. Commands must include expected outcomes.

```bash
python3 -m pytest tests/unit/test_example.py -q
python3 -m pytest tests/behavior/test_example_flow.py -q
grep -R "old_term" src/ | wc -l  # expected: 0
```

### 10. Residual Risks

List what remains uncertain after verification. A residual risk is acceptable only when it is explicit, owned, and bounded. If no residual risk remains, state that explicitly with the evidence basis.

## Compatibility with Other Documentation Formats

EAS should reference or embed existing formats rather than replace them.

| Format | EAS use |
|---|---|
| EARS | Preferred structure for functional requirement rows; use EAS to map those rows to acceptance criteria, evidence, detractor objections, and residual risk. |
| PRD | Intent, users, goals, non-goals, product acceptance. |
| RFC | Alternatives, tradeoffs, unresolved questions. |
| ADR | Durable decisions and consequences. |
| Gherkin | ATDD behavior scenarios. |
| OpenAPI / AsyncAPI | API contract and compatibility checks. |
| Test plan | Unit, behavior, integration, contract, manual, and regression tests. |
| Threat model | Abuse cases, mitigations, and security acceptance. |
| Runbook | Rollout, rollback, metrics, alerts, and operational checks. |

## SDD Integration

EAS can be introduced at different points:

- During `sdd-spec`, create the EAS requirements and acceptance sections.
- During `sdd-tasks`, derive tasks from the gap matrix.
- During `sdd-apply`, implement rows that are not covered.
- During `sdd-verify`, run `scripts/eas_validate.py`, prove every acceptance row, and resolve detractor objections.
- During `sdd-archive`, save the final EAS with evidence and residual risks.

## ATDD and TDD Mapping

EAS is intentionally friendly to both ATDD and TDD. The ATDD path writes user-facing acceptance rows and Gherkin scenarios first, then implements until behavior tests pass. The TDD path decomposes acceptance rows into unit-level tests, then implements incrementally until all mapped tests pass.

## Validator

Run the validator before treating an EAS artifact as complete. Use `--require-ears` when project policy requires functional requirements to follow EARS syntax:

```bash
python3 scripts/eas_validate.py path/to/eas.md
python3 scripts/eas_validate.py --require-ears path/to/eas.md
```

The validator fails if required sections are absent, requirements lack acceptance/evidence coverage, the Detractor is missing, objection disposition is unresolved, verification commands are absent, or residual risks are not explicit. By default it warns when functional requirements are not EARS-like; with `--require-ears`, those warnings become blocking errors.

## Minimum Bar

An EAS is complete enough to use when every requirement has at least one acceptance criterion, every acceptance criterion has a verification method, the gap matrix maps each requirement to evidence, the detractor log has at least one real objection with disposition, residual risks are named or explicitly absent, and `sdd-verify` can decide pass/fail from the artifact without relying on vibes.

## Related Artifacts

- ADR-317: `docs/02-Decisions/adrs/ADR-317-executable-acceptance-specification-eas.md`
- ADR-319: `docs/02-Decisions/adrs/ADR-319-detractor-review-modes.md`
- Template: `templates/eas.md`
- Rule: `rules/eas-evidence-artifact.md`
- Validator: `scripts/eas_validate.py`
- Existing acceptance rule: `rules/acceptance-criteria.md`
- Existing adversarial review rule: `rules/adversarial-review.md`


## External References

- Brookings: [Lessons from Israel's Intelligence Reforms](https://www.brookings.edu/articles/lessons-from-israels-intelligence-reforms/)
- CIA Center for the Study of Intelligence: [Instituting Devil's Advocacy in IC Analysis after the Arab-Israeli War of October 1973](https://www.cia.gov/resources/csi/static/610d592f509c5ad03f5a999827dd9bdb/Article-Instituting-Devils-Advocacy-in-IC-Analysis-after-October-1973-War.pdf)
- de Bono Group: [Six Thinking Hats](https://www.debonogroup.com/services/core-programs/six-thinking-hats/)
- Mollick & Mollick: [Assigning AI: Seven Approaches for Students, with Prompts](https://arxiv.org/abs/2306.10052)
- Microsoft prompts-for-edu: [Devil's Advocate prompt](https://github.com/microsoft/prompts-for-edu/blob/main/Students/Prompts/Devils%20Advocate.MD)
