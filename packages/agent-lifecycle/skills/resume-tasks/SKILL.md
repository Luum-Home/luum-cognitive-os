<!-- SCOPE: both -->
---
name: resume-tasks
description: Check for incomplete tasks from previous sessions and offer to resume them. Use when starting a new session or after a crash.
user-invocable: true
version: 1.0.0
last-updated: 2026-03-21
audience: project
summary_line: Check for incomplete tasks from previous sessions and offer to resume them.

platforms: ["claude-code"]
prerequisites: []
---

# Resume Tasks — Fault Tolerance Recovery

## Purpose

Detect and recover from sub-agent failures. When a session dies mid-work, this skill identifies incomplete tasks and offers to re-launch them.

## Instructions

### Step 1: Read Active Tasks

Read `.claude/tasks/active-tasks.json` from the project root.

If the file doesn't exist or has no tasks, report: "No active tasks found. Nothing to resume."

### Step 2: Identify Incomplete Tasks

Filter tasks where `status` is `"in_progress"` or `"failed"`.

For each incomplete task:

1. **Check if work was actually completed** by running the task's `checkCommand` (if defined):
   ```bash
   eval "$checkCommand"
   ```
   - Exit code 0 = work exists, task may have completed despite session death
   - Non-zero = work is missing, task needs re-launch

2. **Check expectedOutputs** (if defined):
   - For each path in `expectedOutputs`, check if the file exists
   - If ALL expected outputs exist, the task likely completed

3. **Search Engram for context**:
   ```
   mem_search(query: task.description, project: "{project}", limit: 3)
   ```
   - Look for session summaries or observations that indicate the task completed
   - Look for any partial progress notes

### Step 3: Present Summary Table

Show the user a table with ALL tasks (not just incomplete ones):

```
| # | Task Description | Status | Age | Recoverable? | Action |
|---|-----------------|--------|-----|--------------|--------|
| 1 | Migrate users-auth to Go | in_progress | 2h ago | Yes - no outputs found | Re-launch |
| 2 | Add mock for PaymentGateway | failed | 1d ago | Partial - 2/3 files exist | Resume |
| 3 | Update BFF routes | completed | 3h ago | N/A | Done |
```

**Recoverable?** column logic:
- "Yes - no outputs found" = checkCommand failed AND no expectedOutputs exist
- "Partial - N/M files exist" = some expectedOutputs exist but not all
- "Already done" = checkCommand passed OR all expectedOutputs exist (auto-mark as completed)
- "N/A" = task already completed

### Step 4: Auto-Fix Stale Tasks

For tasks where the check reveals work IS done:
- Update the task status to `"completed"` in active-tasks.json
- Set `completedAt` to current timestamp
- Set `outputSummary` to "Auto-recovered: outputs verified present"

### Step 5: Ask User for Re-launch

For genuinely incomplete tasks:
1. Ask: "Which tasks should I re-launch? (enter numbers, 'all', or 'none')"
2. Wait for user response
3. For each approved task:
   a. Search Engram for any partial progress context
   b. Re-launch with the original description + any recovered context
   c. Add a note: "RESUMING: This task was previously started but interrupted. Check if partial work exists before starting fresh."

### Step 6: Clean Up

After processing:
- Remove tasks older than 7 days with status "completed" from active-tasks.json
- Keep failed/in_progress tasks indefinitely until resolved

## Edge Cases

- **Empty tasks file**: Report clean state, nothing to do
- **All tasks completed**: Report "All previous tasks completed successfully"
- **No checkCommand defined**: Assume task is incomplete, ask user
- **Engram unavailable**: Fall back to file-based checks only
