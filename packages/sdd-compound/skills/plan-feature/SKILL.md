---
name: plan-feature
description: Create a feature implementation plan with evaluation scoring. Use before
  implementing any significant feature.
user-invocable: true
version: 1.0.0
audience: project
effort: opus
summary_line: Create a feature implementation plan with evaluation scoring.
platforms:
- claude-code
prerequisites: []
triggers:
- plan-feature
- /plan-feature
- Plan Feature
- Create a feature implementation plan with evaluation scoring
---
<!-- SCOPE: both -->
# Plan Feature

Create a structured implementation plan for a new feature, then self-evaluate it.

## Procedure

### 1. Gather Context

- If no feature description is provided, ask the user what feature to plan
- Identify the target service(s) from the description
- Read relevant source files to understand current architecture
- Check `.cognitive-os/plans/features/` for similar past plans

### 2. Research the Codebase

- Read `cognitive-os.yaml -> project.architecture` for framework, layer, and evaluation criteria config
- Read the service's directory structure
- Identify existing patterns (controllers, use cases, entities, DTOs) based on `project.architecture.layers`
- Check for related tests and their patterns
- Review constitutional gates that apply (`.claude/rules/constitutional-gates.md`)
- Check the current project phase (`cognitive-os.yaml -> project.phase`)

### 3. Write the Plan

Save to `.cognitive-os/plans/features/{YYYY-MM-DD}-{slug}.md` with this format:

```markdown
---
title: {Feature Name}
type: feature
status: draft
score: 0
created: {YYYY-MM-DD}
author: agent
service: {service-name}
---

## Context
{Why this feature is needed, background, user story}

## Approach
{High-level technical approach, architecture decisions}

## Affected Files
{List of files to create/modify with brief description of changes}

## Tasks
- [ ] {Task 1 with concrete deliverable}
- [ ] {Task 2}
- [ ] {Task N}

## Test Strategy
{What tests to write, test patterns to follow, coverage targets}

## Risks
- {Risk 1} -> {Mitigation}
- {Risk 2} -> {Mitigation}

## Rollback Plan
{How to safely revert if something goes wrong}
```

### 4. Self-Evaluate (0-50)

Score the plan on 5 criteria (0-10 each):

| Category | Score | Justification |
|----------|-------|---------------|
| Completeness | X/10 | Are all requirements covered? |
| Feasibility | X/10 | Can be built with current tools and patterns? |
| Risk Assessment | X/10 | Are risks identified with concrete mitigations? |
| Architecture Alignment | X/10 | Follows architecture criteria from `cognitive-os.yaml -> project.architecture.evaluation_criteria`? |
| Test Coverage Plan | X/10 | Tests defined for happy path, edge cases, error cases? |

**Total: X/50**

### 5. Auto-Improve if Needed

- If score < 25: identify weak areas, improve the plan, re-evaluate
- Iterate until score >= 25 or 3 iterations reached
- Update the plan file with improvements and new score

### 6. Present to User

- Show the plan summary and score
- If score >= 25: recommend approval
- If score < 25 after improvements: flag concerns, ask for human guidance
- On user approval: update status to `approved` in frontmatter

## Output

Return the plan file path and evaluation score.
