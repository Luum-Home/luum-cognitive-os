<!-- SCOPE: both -->
---
name: sdd-continue
command: /sdd-continue
description: "Use when you need this Cognitive OS skill: Enhanced SDD continuation with state inspection — determines optimal next action; do not use when a narrower skill directly matches the task."
trigger: User invokes /sdd-continue [change-name], or orchestrator needs to determine next SDD step
inputs:
  - change-name (optional): SDD change to continue. If omitted, scans for any in-progress changes.
outputs:
  - recommended_action: The optimal next SDD phase to run
  - alternatives: Other possible actions ranked by impact
  - state_summary: Current state of all artifacts
  - reasoning: Why the recommended action was chosen
audience: project
effort: opus
version: "1.0.0"
platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\bsdd[- ]?continue\b'
    confidence: 0.96
  - pattern: '\bcontinue\s+(the\s+)?sdd\b'
    confidence: 0.90
  - pattern: '\binspect\s+sdd\s+state\b'
    confidence: 0.84
---

# Enhanced SDD Continue (BMAD v6 Pattern 6)

## Purpose

Intelligently determine the next SDD action by inspecting all available state sources. Unlike a simple "run next phase" approach, this skill considers the full picture: existing artifacts, plan files, workflow state, and in-progress tasks.

## State Sources to Inspect

Before recommending the next action, inspect ALL of these:

### 1. Engram Artifacts
Search for existing SDD artifacts using topic keys:

| Artifact | Topic Key | Required By |
|----------|-----------|-------------|
| Exploration | `planning/{change-name}/explore` | proposal (optional) |
| Proposal | `planning/{change-name}/proposal` | spec, design |
| Spec | `planning/{change-name}/spec` | tasks, verify |
| Design | `planning/{change-name}/design` | tasks |
| Tasks | `planning/{change-name}/tasks` | apply |
| Apply progress | `planning/{change-name}/apply-progress` | verify |
| Verify report | `planning/{change-name}/verify-report` | archive |
| Archive report | `planning/{change-name}/archive-report` | (terminal) |
| DAG state | `planning/{change-name}/state` | (metadata) |

For each topic key, run:
```
mem_search(query: "{topic_key}", project: "{project}")
```

### 2. Plan Files
Check `.cognitive-os/plans/` for existing plans:
```
.cognitive-os/plans/features/{change-name}/
.cognitive-os/plans/bugs/{change-name}/
.cognitive-os/plans/migrations/{change-name}/
.cognitive-os/plans/chores/{change-name}/
```

Look for:
- Plan files with task breakdowns
- Step files indicating progress
- Any README or state files

### 3. Workflow State
Check `.cognitive-os/workflows/state/` for workflow tracking:
- Active workflow runs
- Completed phases
- Failed phases that need retry

### 4. Active Tasks
Read `.cognitive-os/tasks/active-tasks.json` for:
- Tasks currently in progress
- Tasks blocked on dependencies
- Tasks related to the change

## Decision Logic

Based on the state inspection, determine the optimal next action:

### If NO artifacts exist:
- **Recommend**: `sdd-explore` or `sdd-propose`
- **Reasoning**: Starting from scratch, need to define the change

### If ONLY proposal exists:
- **Recommend**: `sdd-spec` AND `sdd-design` (can run in parallel)
- **Reasoning**: Proposal is ready, need spec and design before tasks

### If proposal + spec exist, but NO design:
- **Recommend**: `sdd-design`
- **Reasoning**: Design is required for task breakdown

### If proposal + design exist, but NO spec:
- **Recommend**: `sdd-spec`
- **Reasoning**: Spec is required for task breakdown

### If spec + design exist, but NO tasks:
- **Recommend**: `sdd-tasks`
- **Reasoning**: Ready for task breakdown

### If tasks exist, but NO apply-progress:
- **Recommend**: `/readiness-check` then `sdd-apply`
- **Reasoning**: Ready for implementation, but must pass readiness gate first

### If apply-progress exists (partial):
- **Recommend**: Resume `sdd-apply`
- **Reasoning**: Implementation started but not complete, resume from checkpoint

### If apply-progress exists (complete), but NO verify:
- **Recommend**: `sdd-verify`
- **Reasoning**: Implementation complete, needs verification

### If verify report exists, but NO archive:
- **Recommend**: `sdd-archive`
- **Reasoning**: Verification done, ready to archive

### If ALL artifacts exist:
- **Recommend**: Nothing — change is complete
- **Reasoning**: All phases completed

## Output Format

```yaml
change: {change-name}
state:
  exploration: FOUND | NOT_FOUND
  proposal: FOUND | NOT_FOUND
  spec: FOUND | NOT_FOUND
  design: FOUND | NOT_FOUND
  tasks: FOUND | NOT_FOUND
  apply_progress: FOUND | NOT_FOUND | PARTIAL
  verify_report: FOUND | NOT_FOUND
  archive_report: FOUND | NOT_FOUND
  plan_files: FOUND | NOT_FOUND
  active_tasks: {count} related tasks
  workflow_state: ACTIVE | IDLE | FAILED

recommended_action:
  phase: {sdd-phase or skill}
  reasoning: "{why this is the best next step}"
  prerequisites: ["{any prerequisites that need attention}"]
  estimated_complexity: LOW | MEDIUM | HIGH

alternatives:
  - phase: {alternative-1}
    reasoning: "{why this could also be done}"
    impact: HIGH | MEDIUM | LOW
  - phase: {alternative-2}
    reasoning: "{why this could also be done}"
    impact: HIGH | MEDIUM | LOW
```

## No Change Name Provided

If no change-name is given, scan engram for ALL in-progress changes:
```
mem_search(query: "sdd/", project: "{project}")
```

List all changes with their current state and recommend which one to continue first, prioritizing:
1. Changes with FAILED phases (need attention)
2. Changes closest to completion (quick wins)
3. Changes with the most artifacts (most invested effort)

## Integration with Orchestrator

The orchestrator uses this skill's output to:
1. Determine which SDD phase to delegate next
2. Provide context about what exists to the sub-agent
3. Detect stalled or abandoned changes
4. Report progress to the user with full state visibility
