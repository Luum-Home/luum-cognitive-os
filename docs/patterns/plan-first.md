# Plan-First Development Protocol

## When to Create a Plan

| Task Size | Needs Plan? | Auto-Evaluate? |
|-----------|-------------|----------------|
| Bug fix (< 5 files) | No | No |
| Small feature (1 service) | Optional | No |
| Medium feature (2-3 services) | Yes | Yes |
| Large feature (4+ services) | Yes + human review | Yes |
| Migration/refactor | Always | Always |
| Architecture change | Always + squad review | Always |

## Plan-First Enforcement

In phase `reconstruction`: Plans are optional (we're rebuilding fast)
In phase `stabilization`: Plans required for medium+ tasks
In phase `production`: Plans required for ALL changes
In phase `maintenance`: Plans required, human approval for anything > bug fix

## How Plans Work

1. Agent creates plan via `/plan-feature` or `/plan-bug` skill
2. Plan is saved to `.cognitive-os/plans/{type}/{date}-{slug}.md`
3. Plan is auto-evaluated (scored 0-50 on 5 criteria)
4. If score < 25: plan is auto-improved before implementation
5. If score >= 25: plan is ready for implementation
6. After implementation: plan stays as historical record

## Plan Types and Directories

| Type | Directory | Skill |
|------|-----------|-------|
| Feature | `.cognitive-os/plans/features/` | `/plan-feature` |
| Bug fix | `.cognitive-os/plans/bugs/` | `/plan-bug` |
| Chore | `.cognitive-os/plans/chores/` | (manual) |
| Migration | `.cognitive-os/plans/migrations/` | (via workflow) |

## Evaluation Criteria

| Category | Max | What It Checks |
|----------|-----|---------------|
| Completeness | 10 | All requirements covered? |
| Feasibility | 10 | Can be built with current tools? |
| Risk Assessment | 10 | Risks identified with mitigations? |
| Architecture Alignment | 10 | Follows clean architecture + declared framework? |
| Test Coverage Plan | 10 | Tests defined for all scenarios? |

## Integration with Workflows

The `.cognitive-os/workflows/` pipeline automatically uses the plan system:
- Feature pipeline writes plans to `.cognitive-os/plans/features/`
- Bug pipeline writes plans to `.cognitive-os/plans/bugs/`
- Migration pipeline writes plans to `.cognitive-os/plans/migrations/`
- Evaluation phase scores plans and writes to `.cognitive-os/plans/evaluations/`

## Integration with Engram

After a plan is completed (implemented successfully):
- Save lessons learned to Engram with topic_key `plan-lessons/{slug}`
- Include: what worked, what didn't, actual vs estimated effort
- This feeds into future plan quality improvement
