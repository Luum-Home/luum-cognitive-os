<!-- SCOPE: both -->
---
name: plan-bug
description: Create a bug fix plan with root cause analysis and evaluation scoring. Use before fixing any non-trivial bug.
user-invocable: true
version: 1.0.0
audience: project
effort: opus
summary_line: Create a bug fix plan with root cause analysis and evaluation scoring.

platforms: ["claude-code"]
prerequisites: []
---

# Plan Bug Fix

Create a structured bug fix plan with root cause analysis, then self-evaluate it.

## Procedure

### 1. Gather Context

- If no bug description is provided, ask the user what bug to fix
- Identify the target service(s) from the description
- Check error logs, stack traces, or reproduction steps provided
- Check `.cognitive-os/plans/bugs/` for similar past bug fixes

### 2. Load Architecture Config

- Read `cognitive-os.yaml -> project.architecture` for frameworks, layers, and evaluation criteria
- These drive the Architecture Alignment scoring in Step 4 (no hardcoded framework names)

### 3. Root Cause Analysis

- Read relevant source files where the bug manifests
- Trace the code path from entry point to failure
- Identify the root cause (not just symptoms)
- Check if the bug exists in other similar code paths
- Search Engram for related past fixes: `mem_search(query: "bugfix {service} {symptoms}")`

### 4. Write the Plan

Save to `.cognitive-os/plans/bugs/{YYYY-MM-DD}-{slug}.md` with this format:

```markdown
---
title: {Bug Description}
type: bug
status: draft
score: 0
created: {YYYY-MM-DD}
author: agent
service: {service-name}
severity: critical|high|medium|low
---

## Bug Report
{What is happening vs what should happen}

## Root Cause Analysis
{Why the bug occurs, what code path leads to the failure}

## Reproduction Steps
1. {Step 1}
2. {Step 2}
3. {Expected vs actual behavior}

## Fix Approach
{How to fix the root cause, not just the symptom}

## Affected Files
{List of files to modify with description of changes}

## Tasks
- [ ] {Fix task 1}
- [ ] {Write/update test for the bug}
- [ ] {Verify fix in related code paths}

## Test Strategy
- [ ] Unit test reproducing the bug (red -> green)
- [ ] Regression test for similar code paths
- [ ] Integration test if cross-service

## Risks
- {Risk 1} -> {Mitigation}

## Rollback Plan
{How to revert safely}
```

### 5. Self-Evaluate (0-50)

Score the plan on 5 criteria (0-10 each):

| Category | Score | Justification |
|----------|-------|---------------|
| Completeness | X/10 | Root cause identified? All affected paths checked? |
| Feasibility | X/10 | Fix is straightforward and testable? |
| Risk Assessment | X/10 | Side effects considered? Rollback plan clear? |
| Architecture Alignment | X/10 | Fix follows architecture criteria from `cognitive-os.yaml -> project.architecture.evaluation_criteria`? No violations of configured frameworks/layers? |
| Test Coverage Plan | X/10 | Bug reproduction test + regression tests defined? |

**Total: X/50**

### 6. Auto-Improve if Needed

- If score < 25: identify weak areas, improve the plan, re-evaluate
- Focus on root cause depth and test coverage
- Update the plan file with improvements and new score

### 7. Present to User

- Show root cause analysis and fix approach
- Show score and any concerns
- On user approval: update status to `approved`

## Output

Return the plan file path and evaluation score.
