# Plan System

The plan system provides structured planning, evaluation, and archival for all significant development tasks.

## Why Plans Exist

1. **Trazabilidad**: Every decision is documented with rationale, not just code
2. **Reproducibilidad**: Plans can be re-applied or adapted for similar future tasks
3. **Learning**: Evaluations capture what makes a good plan, improving over time
4. **Quality gate**: The 0-50 scoring system catches incomplete or risky plans before implementation

## Creating Plans

### Via Skills (recommended)

```
/plan-feature    -- Interactive feature planning with auto-evaluation
/plan-bug        -- Bug fix planning with root cause analysis
/evaluate-plan   -- Score any existing plan 0-50
```

### Via Workflows (automatic)

The `.cognitive-os/workflows/` pipelines create plans automatically during their `plan` phase:
- Feature pipeline -> `.cognitive-os/plans/features/`
- Bug pipeline -> `.cognitive-os/plans/bugs/`
- Migration pipeline -> `.cognitive-os/plans/migrations/`

### Manually

Create a markdown file in the appropriate directory following the format in `.cognitive-os/plans/README.md`.

## Evaluation Scoring System

Plans are scored 0-50 across 5 categories (0-10 each):

| Category | What It Checks |
|----------|---------------|
| **Completeness** | Requirements coverage, task granularity, affected files listed |
| **Feasibility** | Buildable with current tools, realistic scope, dependencies addressed |
| **Risk Assessment** | Risks identified, mitigations concrete, rollback plan exists |
| **Architecture Alignment** | Clean architecture layers, correct framework usage, constitutional gates |
| **Test Coverage Plan** | Unit tests, integration tests, edge cases, error scenarios |

### Score Thresholds

| Score | Verdict | Action |
|-------|---------|--------|
| 0-24 | NEEDS_REVISION | Auto-improve plan, then re-evaluate |
| 25-34 | APPROVED | Implement with minor concerns noted |
| 35-44 | APPROVED | Solid plan, implement confidently |
| 45-50 | APPROVED | Excellent plan |

### Auto-Improvement

When a plan scores < 25, the system:
1. Identifies the weakest categories
2. Proposes specific improvements
3. Rewrites the weak sections
4. Re-evaluates (up to 3 iterations)

## Integration with Engram

Plans connect to the persistent memory system:

- **Before planning**: Search Engram for similar past plans and their outcomes
- **After completion**: Save lessons learned with topic_key `plan-lessons/{slug}`
- **Pattern detection**: Recurring low scores in a category trigger skill adaptation

## Directory Structure

```
.cognitive-os/plans/
  README.md              -- Format specification and scoring criteria
  features/              -- Feature implementation plans
  bugs/                  -- Bug fix plans (include root cause analysis)
  chores/                -- Maintenance and refactoring plans
  migrations/            -- Database and service migration plans
  evaluations/           -- Evaluation reports with scores
```

## Plan Lifecycle

```
draft -> evaluated -> approved -> implementing -> completed
                  \-> needs_revision -> (auto-improve) -> evaluated
```

## Enforcement Rules

See `.cognitive-os/rules/plan-first.md` for when plans are required based on task size and project phase.

## File Naming Convention

Plans: `{YYYY-MM-DD}-{slug}.md` (e.g., `2026-03-22-add-transfer-endpoint.md`)
Evaluations: `{YYYY-MM-DD}-{plan-slug}-eval.md` (e.g., `2026-03-22-add-transfer-endpoint-eval.md`)
