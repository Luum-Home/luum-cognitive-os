<!-- SCOPE: both -->
---
name: auto-refine
description: Analyze a failed agent's output, determine root cause, and re-launch with refined instructions. Implements the PITER Refine step.
version: 1.0.0
user-invocable: true
auto-generated: false
audience: project
summary_line: "Analyze a failed agent's output, determine root cause, and re-launch with…"

platforms: ["claude-code"]
prerequisites: []
---

# Auto-Refine Skill

Closes the PITER loop by analyzing agent failures and re-launching with corrective context.

## When to Use

- When an agent task fails and the `auto-refine.sh` hook signals `ORCHESTRATOR ACTION REQUIRED`
- Manually via `/auto-refine` when you want to retry a failed agent with better instructions
- After the orchestrator receives an escalation and the human approves a retry

## Instructions

### Step 1: Identify the Failed Task

Locate the failure context from one of these sources (in priority order):

1. **Hook output**: If `auto-refine.sh` just fired, the retry context is in the hook's stdout
2. **active-tasks.json**: Check `.cognitive-os/tasks/active-tasks.json` for tasks with `status: "failed"`
3. **Engram**: Search for recent agent failures via `mem_search(query: "agent failed", project: "{project}")`
4. **User-provided**: The user may paste the error output directly

Extract:
- **Original task description**: What the agent was supposed to do
- **Failure type**: TEST_FAILURE, BUILD_ERROR, LINT_ERROR, COVERAGE_FAILURE, AGENT_ERROR
- **Error details**: The specific error messages
- **Attempt number**: Which retry this is (1, 2, or 3)
- **Previous attempts**: What was tried before (if available from history file)

### Step 2: Analyze the Failure

Determine the root cause category:

| Category | Signal | Refinement Strategy |
|----------|--------|---------------------|
| Code bug | Test assertion fails, wrong output | Fix the logic, not the test |
| Missing import/dep | Module not found, cannot resolve | Add dependency, fix import path |
| Type error | TS/Go type mismatch | Fix type annotations or casting |
| Architecture violation | Wrong layer, wrong pattern | Restructure per architecture rules |
| Test infrastructure | Connection refused, timeout | Check infra is running, add mocks |
| Scope issue | Error in unrelated code | Narrow scope, don't touch unrelated files |
| Flaky test | Passes sometimes | Add retries, fix race conditions |

### Step 3: Build Refined Instructions

Construct a new agent prompt that includes:

```
## Task (Retry {N}/3)

### Original Task
{original task description}

### Previous Failure
Type: {failure type}
Error: {error details}

### What Was Tried
{summary of previous attempts if available}

### Root Cause Analysis
{your analysis from Step 2}

### Refined Approach
{specific instructions on what to do differently}

### Constraints
- Do NOT repeat the same approach that already failed
- Focus on the root cause, not symptoms
- Run verification BEFORE claiming completion
- If you discover the task scope needs changing, say so instead of forcing a fix

### Success Criteria
{same criteria as original, plus any additional checks}

### Verification
{same commands as original}
```

### Step 4: Re-Launch the Agent

Delegate the refined task to a sub-agent with the constructed prompt.

Include:
- The original skill reference (if the original agent used a skill)
- Phase context from `cognitive-os.yaml`
- Error pattern warnings from `error-pattern-detector.sh` (if applicable)

### Step 5: Track the Refinement

After the re-launched agent completes:

1. **If success**:
   - Log to Engram: `mem_save(title: "Auto-refined: {task}", type: "bugfix", content: ...)`
   - Clean up retry files in `.cognitive-os/metrics/auto-refine/`

2. **If failure (attempt < 3)**:
   - The `auto-refine.sh` hook will fire again automatically
   - The orchestrator loops back to Step 1

3. **If failure (attempt = 3)**:
   - The hook will output an ESCALATION
   - Report to the human with full attempt history
   - Include: all 3 attempts, all errors, your root cause hypothesis, recommended human action

## Refinement History

Retry tracking files are stored in `.cognitive-os/metrics/auto-refine/`:
- `{fingerprint}.count` — Current retry count (0-3)
- `{fingerprint}.history` — JSONL of each attempt with type, timestamp, details

These are automatically cleaned up on success or after escalation.

## Phase-Aware Behavior

| Phase | Auto-Refine Behavior |
|-------|---------------------|
| reconstruction | Always auto-retry. Agents fix their own work. |
| stabilization | Always auto-retry. Agents fix their own work. |
| production | Detect failure, suggest retry, but require human approval before re-launch. |
| maintenance | Detect failure, suggest retry, but require human approval before re-launch. |

## Anti-Patterns

- Do NOT retry with the exact same instructions (definition of insanity)
- Do NOT increase scope on retry (fix the original task, don't add features)
- Do NOT skip verification on the final attempt ("it should work now")
- Do NOT auto-refine tasks that failed due to missing infrastructure (fix infra first)
- Do NOT retry if the error is in code the agent didn't write (escalate instead)

## Engram Integration

After a successful auto-refinement, save the learning:

```
mem_save(
  title: "Auto-refined: {brief task description}",
  type: "bugfix",
  project: "{project}",
  topic_key: "auto-refine/{service-or-component}",
  content: "**What**: {task} failed {N} times, then succeeded\n**Why**: Root cause was {cause}\n**Where**: {files affected}\n**Learned**: {what the refinement discovered that the original attempt missed}"
)
```
