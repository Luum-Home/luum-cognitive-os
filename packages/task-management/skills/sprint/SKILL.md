<!-- SCOPE: both -->
---
name: sprint
description: Lightweight agent-managed sprint tracking — plan, status, retro, course-correct
invoke: /sprint
version: 1.0.0
model: sonnet
tags: [planning, tracking, workflow]
audience: project
platforms: ["claude-code"]
prerequisites: []
---

# Sprint Tracking (BMAD v6 Pattern 10)

Lightweight sprint management for agent-driven development. Not human Scrum — this tracks what the agent team is working on across sessions.

## State File

Sprint state is persisted in `.cognitive-os/workflows/state/sprint-status.yaml`.

## Sub-Commands

### `/sprint plan`

Create or update the current sprint plan.

**Input**: Sprint goal (from user or derived from backlog)

**Steps**:
1. Read current sprint state (if exists)
2. If active sprint exists: warn and ask to close it first
3. Create new sprint with:
   - `sprint_id`: `{year}-w{week}` (e.g., `2026-w12`)
   - `goal`: one-sentence sprint goal
   - `stories`: list of stories with `id`, `title`, `status` (planned/in_progress/completed/blocked)
   - `start_date`: today
   - `end_date`: +7 days (default, overridable)
4. Write to `sprint-status.yaml`
5. Save to Engram under `sprint/{sprint_id}/goal`

**Output**:
```
SPRINT PLANNED: {sprint_id}
Goal: {goal}
Stories: {count} planned
Duration: {start} → {end}
```

### `/sprint status`

Show current sprint progress.

**Steps**:
1. Read `sprint-status.yaml`
2. Calculate: stories completed / total, blocked count, days remaining
3. Assess: on track / at risk / behind

**Output**:
```
SPRINT STATUS: {sprint_id}
Goal: {goal}
Progress: {completed}/{total} stories ({percent}%)
  Completed: {list}
  In Progress: {list}
  Blocked: {list}
  Planned: {list}
Days Remaining: {days}
Assessment: {on_track|at_risk|behind}
```

### `/sprint retro`

Generate a retrospective for the current or last sprint.

**Steps**:
1. Read `sprint-status.yaml`
2. Analyze: completion rate, blocked stories, time per story (if tracked)
3. Search Engram for errors/fixes during sprint period
4. Generate retrospective

**Output**:
```
SPRINT RETRO: {sprint_id}

## What Went Well
- {item}

## What Didn't Go Well
- {item}

## Action Items
- [ ] {actionable improvement}

## Metrics
- Completion Rate: {percent}%
- Stories Completed: {n}/{total}
- Blocked Stories: {n}
- Avg Time per Story: {estimate if available}
```

5. Save retro to Engram under `sprint/{sprint_id}/retro`

### `/sprint correct`

Mid-sprint course correction.

**Steps**:
1. Read current sprint status
2. Identify: blocked stories, stories at risk, scope creep
3. Propose adjustments:
   - Descope stories that won't fit
   - Unblock stories with workarounds
   - Re-prioritize remaining work
4. Update `sprint-status.yaml` with corrections
5. Save correction to Engram under `sprint/{sprint_id}/correction`

**Output**:
```
SPRINT CORRECTION: {sprint_id}

## Changes Made
- {descoped/reprioritized/unblocked}: {story}

## Updated Assessment
Progress: {completed}/{new_total} stories
Assessment: {on_track|at_risk|behind}
```

## Story Status Transitions

```
planned → in_progress → completed
    │          │
    │          └→ blocked → in_progress (after unblock)
    │
    └→ descoped (via /sprint correct)
```

## State File Schema

```yaml
# .cognitive-os/workflows/state/sprint-status.yaml
current_sprint:
  sprint_id: "2026-w12"
  goal: "Complete auth refactor and add biometric login"
  start_date: "2026-03-16"
  end_date: "2026-03-23"
  stories:
    - id: "S001"
      title: "Refactor JWT validation in BFF"
      status: completed      # planned | in_progress | completed | blocked | descoped
      assigned_to: null      # agent name if applicable
      notes: ""
    - id: "S002"
      title: "Add biometric auth endpoint"
      status: in_progress
      assigned_to: null
      notes: "Waiting on Keycloak config"
  corrections: []
  retro: null

previous_sprints:
  - sprint_id: "2026-w11"
    goal: "..."
    completion_rate: 75
    retro_saved: true
```

## Integration

- **Engram**: Sprint goals and retros persisted under `sprint/{sprint_id}/`
- **Agent KPIs**: Sprint completion rate feeds into agent efficiency metrics
- **Resume Tasks**: `/resume-tasks` checks sprint status for incomplete stories
- **Retrospective skill**: `/retrospective` can pull sprint data for broader analysis

## Auto-Triggers

- Session start: if active sprint exists, show brief status summary
- Story completion: update `sprint-status.yaml` automatically when task is marked done
- End of sprint period: suggest running `/sprint retro`
