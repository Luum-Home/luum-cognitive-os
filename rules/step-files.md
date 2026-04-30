<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Step-File Architecture for Long Phases (BMAD v6 Pattern 5)

## Purpose

Long-running agent phases risk context loss from compaction or session interruption. Step files break a phase into discrete, resumable units of work. Each step is a checkpoint that enables resumption without re-doing completed work.

## When to Use Step Files

Use step files when a phase meets ANY of these criteria:
- Estimated duration > 30 minutes
- More than 5 distinct actions required
- Multiple files need modification across different services
- Phase involves sequential dependencies (step N depends on step N-1)
- High risk of context window exhaustion

Do NOT use step files for:
- Single-file changes
- Quick fixes (< 10 minutes)
- Read-only analysis tasks
- Tasks with fewer than 3 actions

## Directory Structure

Step files live inside the relevant workflow or plan directory:

```
.cognitive-os/workflows/steps/{workflow-name}/
  step-01-{description}.md
  step-02-{description}.md
  ...
  step-XX-complete.md
```

Or for SDD phases:

```
.cognitive-os/plans/{category}/{change-name}/steps/
  step-01-{description}.md
  step-02-{description}.md
  ...
  step-XX-complete.md
```

## Step File Naming

- Prefix: `step-{NN}-` where NN is zero-padded (01, 02, ..., 99)
- Suffix: kebab-case description of the step's purpose
- Final step is ALWAYS `step-XX-complete.md` (XX = next number after last action step)
- Examples:
  - `step-01-create-entity.md`
  - `step-02-implement-repository.md`
  - `step-03-write-usecase.md`
  - `step-04-add-controller.md`
  - `step-05-write-tests.md`
  - `step-06-complete.md`

## Step File Content Format

Each step file MUST contain:

```markdown
# Step {NN}: {Title}

## Status
<!-- PENDING | IN_PROGRESS | COMPLETED | FAILED -->
PENDING

## Objective
{What this step accomplishes — one sentence}

## Inputs
- {What this step needs from previous steps or external sources}

## Actions
1. {Specific action to take}
2. {Next action}
3. ...

## Outputs
- {What this step produces — files created, artifacts generated}

## Success Criteria
- [ ] {Criterion 1}
- [ ] {Criterion 2}

## Notes
{Any observations, decisions, or issues encountered during execution}
```

## Resumption Protocol

When an agent starts (or resumes) a step-file workflow:

1. **Scan steps directory**: List all `step-*.md` files in order
2. **Find last completed step**: Look for the highest-numbered step with `Status: COMPLETED`
3. **Check for in-progress step**: If a step is `IN_PROGRESS`, resume from that step
4. **Start next pending step**: If no in-progress step, start the next `PENDING` step
5. **Mark completion**: Update step status to `COMPLETED` after all success criteria are met
6. **Final step**: When `step-XX-complete.md` is reached, mark the entire workflow as done

## Agent Behavior

### Starting a Step
1. Read the step file
2. Update status from `PENDING` to `IN_PROGRESS`
3. Execute the actions listed
4. Check success criteria

### Completing a Step
1. Verify all success criteria are met
2. Update status from `IN_PROGRESS` to `COMPLETED`
3. Fill in the Notes section with any observations
4. Proceed to next step

### Handling Failure
1. Update status to `FAILED`
2. Document the failure in Notes
3. Report to orchestrator for decision:
   - Retry the step with modifications
   - Skip and continue (if non-critical)
   - Halt the workflow

## Orchestrator Integration

The orchestrator uses step files to:
- Track progress of delegated long-running tasks
- Resume work after session interruption or compaction
- Report granular progress to the user
- Decide whether to re-launch a failed step or escalate

## Engram Persistence

For critical workflows, step status should also be saved to engram:
```
topic_key: "workflow/{workflow-name}/progress"
content: "Steps completed: 1-4 of 6. Current: step-05. Blockers: none."
```

This enables cross-session recovery even if step files are not accessible.
