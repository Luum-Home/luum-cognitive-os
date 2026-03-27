# Cognitive OS Plans Archive

Every significant task goes through a plan-evaluate-implement cycle.
Plans are stored here as the single source of truth for what was decided and why.

## How It Works

1. **Create Plan**: Agent writes a plan to `plans/{type}/{YYYY-MM-DD}-{slug}.md`
2. **Evaluate**: Plan is scored 0-50 on completeness, feasibility, risk
3. **Apply**: If score >= 25, implement. If < 25, auto-improve plan first.
4. **Archive**: After implementation, plan stays as historical record.

## Plan Format

```markdown
---
title: Feature Name
type: feature|bug|chore|migration
status: draft|evaluated|approved|implementing|completed
score: 0-50
created: YYYY-MM-DD
author: agent|human
service: wallet|<consumer-codename-b>|etc
---

## Context
Why this is needed.

## Approach
How we'll solve it.

## Tasks
- [ ] Task 1
- [ ] Task 2

## Risks
- Risk 1 -> mitigation

## Evaluation
Score: X/50
- Completeness: X/10
- Feasibility: X/10
- Risk Assessment: X/10
- Architecture Alignment: X/10
- Test Coverage Plan: X/10
```

## Evaluation Criteria

| Category | Max Score | What It Checks |
|----------|----------|---------------|
| Completeness | 10 | All requirements covered? |
| Feasibility | 10 | Can be built with current tools? |
| Risk Assessment | 10 | Risks identified with mitigations? |
| Architecture Alignment | 10 | Follows clean architecture + ginext? |
| Test Coverage Plan | 10 | Tests defined for all scenarios? |

## Directory Structure

```
plans/
  features/      <- Feature implementation plans
  bugs/          <- Bug fix plans
  chores/        <- Maintenance/refactoring plans
  migrations/    <- Database/service migration plans
  evaluations/   <- Plan evaluations with scores
```

## Integration

- **Workflows**: `.cognitive-os/workflows/` pipelines write plans here automatically
- **Skills**: `/plan-feature`, `/plan-bug`, `/evaluate-plan` create and score plans
- **Engram**: Lessons learned from plans feed into persistent memory
- **Rules**: `plan-first.md` enforces plan creation based on task size and project phase
