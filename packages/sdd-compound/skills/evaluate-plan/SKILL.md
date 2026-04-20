<!-- SCOPE: both -->
---
name: evaluate-plan
description: Evaluate any existing plan file with a 0-50 scoring system. Proposes improvements if score is low.
user-invocable: true
version: 1.0.0
audience: project
effort: opus
---

# Evaluate Plan

Score an existing plan on 5 criteria (0-50 total) and propose improvements if needed.

## Procedure

### 0. Load Architecture Config

Read `cognitive-os.yaml -> project.architecture` to get:
- `frameworks` — expected framework per language (used in Architecture Alignment scoring)
- `layers` — expected layer structure (domain, application, infrastructure, dtos)
- `evaluation_criteria` — list of architecture criteria to evaluate against

If `cognitive-os.yaml` is missing or `project.architecture` is not set, use generic clean architecture principles as fallback.

### 1. Locate the Plan

- Accept a plan file path as argument, or
- List recent plans from `.cognitive-os/plans/` and let user choose
- Read the full plan content

### 2. Score on 5 Criteria (0-10 each)

#### Completeness (0-10)
- Are all requirements covered?
- Are affected files listed?
- Are tasks concrete and actionable?
- Is the context/background sufficient?

#### Feasibility (0-10)
- Can this be built with current tools and patterns?
- Are there dependency issues?
- Is the scope realistic for one PR?
- Are external service dependencies addressed?

#### Risk Assessment (0-10)
- Are risks identified?
- Do mitigations exist for each risk?
- Is there a rollback plan?
- Are edge cases considered?
- For financial operations: idempotency and audit trail?

#### Architecture Alignment (0-10)

Read criteria from `cognitive-os.yaml -> project.architecture.evaluation_criteria`. If config is missing, fall back to generic clean architecture principles. Evaluate each criterion from the config list. The default criteria check:

- Follows clean architecture layers from `project.architecture.layers`?
- Uses correct framework per language from `project.architecture.frameworks`?
- DTOs in the right layer (from `project.architecture.layers.dtos`)?
- Respects constitutional gates?
- Dependencies flow inward (infra -> app -> domain)?

#### Test Coverage Plan (0-10)
- Unit tests for business logic?
- Integration tests for cross-service flows?
- Edge case tests?
- Error scenario tests?
- Test patterns match existing codebase?

### 3. Write Evaluation

Save to `.cognitive-os/plans/evaluations/{YYYY-MM-DD}-{plan-slug}-eval.md`:

```markdown
---
plan: {relative path to plan file}
evaluator: agent
date: {YYYY-MM-DD}
score: {total}/50
verdict: APPROVED|NEEDS_REVISION
---

## Evaluation Summary

**Overall Score: {total}/50**
**Verdict: {APPROVED if >= 25, NEEDS_REVISION if < 25}**

## Scoring Breakdown

| Category | Score | Notes |
|----------|-------|-------|
| Completeness | X/10 | {Brief justification} |
| Feasibility | X/10 | {Brief justification} |
| Risk Assessment | X/10 | {Brief justification} |
| Architecture Alignment | X/10 | {Brief justification} |
| Test Coverage Plan | X/10 | {Brief justification} |

## Strengths
- {What the plan does well}

## Improvements Needed
- {Specific, actionable improvement 1}
- {Specific, actionable improvement 2}

## Recommendation
{Next steps: approve, revise specific sections, or reject with reasons}
```

### 4. If Score < 25: Propose Improvements

- List specific sections that need work
- Provide concrete suggestions (not vague feedback)
- Offer to auto-improve the plan and re-evaluate
- If the user approves auto-improvement, update the plan and create a new evaluation

### 5. Update Plan Status

- Update the plan's frontmatter: `score: {total}` and `status: evaluated`
- If approved (>= 25): suggest changing status to `approved`

## Output

Return the evaluation file path, score, and verdict.
