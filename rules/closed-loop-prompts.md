# Closed-Loop Prompts — Self-Correcting Agent Execution

> Source: "Tactical Agentic Coding" by IndyDevDan (agenticengineer.com)

## Principle

Every agent prompt should include three elements that enable self-correction without human intervention:

1. **Success criteria**: How the agent knows the task is done correctly
2. **Verification command**: A concrete command to check the result
3. **Fallback action**: What to do if verification fails

## Prompt Structure

When the orchestrator launches a sub-agent, the prompt MUST include:

```
## Task
{description of what to do}

## Success Criteria
- [ ] {concrete, verifiable condition 1}
- [ ] {concrete, verifiable condition 2}
- [ ] {concrete, verifiable condition 3}

## Verification
Run these commands to verify success:
```
{command 1}
{command 2}
```

## On Failure
If verification fails:
1. Analyze the error output
2. Identify root cause
3. Attempt fix (max {N} attempts)
4. If still failing after {N} attempts: stop and report diagnosis
```

## Refinement Loop Protocol

### Default Behavior (max 3 attempts)

```
Attempt 1: Execute task → Verify
    |
    ├── Pass → Done
    └── Fail → Analyze error
              |
              v
Attempt 2: Adjusted approach → Verify
    |
    ├── Pass → Done
    └── Fail → Analyze error (different from attempt 1?)
              |
              ├── Same error → Escalate (no progress)
              └── Different error → Continue
                    |
                    v
Attempt 3: Further adjusted → Verify
    |
    ├── Pass → Done
    └── Fail → Escalate with full diagnosis
```

### Escalation Criteria (stop looping immediately)

- Same error on consecutive attempts (no progress detected)
- Error requires changes outside agent scope (different service, infrastructure)
- Test infrastructure is broken (not the code under development)
- Token budget exceeded for this task
- Architectural change needed (not a code fix)

### Escalation Report Format

When escalating to human, provide:

```
## Escalation: {task name}

### Attempts Made
1. {what was tried} → {what failed}
2. {what was tried} → {what failed}
3. {what was tried} → {what failed}

### Root Cause Analysis
{why the agent believes it cannot resolve this}

### Recommended Human Action
{specific steps the human should take}

### Files Affected
- {file path} — {what was changed and why}
```

## Auto-Refine Protocol (PITER Integration)

Every agent prompt MUST include auto-refine instructions. This closes the PITER loop
(Evaluate -> Refine) so agents fix their own work instead of stopping at evaluation.

### Mandatory Prompt Additions

When launching any sub-agent, the orchestrator MUST append:

```
## Auto-Refine Protocol
If tests, build, or lint fail after your changes:
1. Analyze the error output — identify root cause, not just symptoms
2. Fix the issue and re-run verification
3. Repeat up to 3 times before reporting failure
4. On each retry, use a DIFFERENT approach if the same fix didn't work

Success = ALL of these pass:
- Tests pass (relevant test suite for the service)
- Build compiles without errors
- No new lint errors introduced
- Coverage not decreased (if measurable)

If you exhaust 3 attempts:
- STOP attempting fixes
- Report with: what you tried, what failed, your root cause hypothesis
- Include the full error output from the last attempt
```

### Auto-Refine Hook

The `auto-refine.sh` PostToolUse hook enforces this at the infrastructure level:
- Detects failure indicators in agent output (FAIL, ERROR, build failed, etc.)
- Tracks retry count per agent task (max 3)
- In reconstruction/stabilization: outputs retry instructions for the orchestrator
- In production/maintenance: suggests retry but requires human approval
- Resets retry count on success
- Escalates to human after 3 failures with full attempt history

### Orchestrator Responsibility

When the auto-refine hook outputs `ORCHESTRATOR ACTION REQUIRED`:
1. Re-launch the SAME agent with the error context provided by the hook
2. Include the original task description PLUS the refinement instructions
3. Do NOT start a new/different task — complete the current one first
4. After 3 failed retries (escalation), report to the human with the full diagnosis

## HALT-and-WAIT Protocol (BMAD v6 Pattern 7)

For ambiguous or high-risk tasks, agents MUST present their plan and WAIT for explicit approval before executing. This prevents unintended damage from misinterpreted instructions.

### HALT Triggers

An agent MUST halt and wait when any of these conditions are true:

| Trigger | Why |
|---------|-----|
| Task touches multiple services | Cross-service changes have blast radius |
| Task involves data migration | Data loss is irreversible |
| Task changes API contracts | Breaks downstream consumers |
| Task modifies auth/security | Security regressions are critical |
| Task deletes or overwrites files at scale | Destructive operations need confirmation |
| Task modifies infrastructure config | Wrong config = service outage |

### HALT Format

When a HALT trigger is detected, the agent outputs:

```
PLAN: [concise description of what the agent will do, including files affected]
SCOPE: [services/packages/files that will be modified]
RISK: [what could go wrong if the plan is wrong]

HALT: Waiting for approval before executing.
```

The agent MUST NOT proceed until it receives explicit approval from the orchestrator or human.

### Phase-Dependent HALT Behavior

| Phase | HALT Scope |
|-------|------------|
| `reconstruction` | HALT only for data-destructive operations (delete, migrate, overwrite production data) |
| `stabilization` | HALT for data-destructive + cross-service changes |
| `production` | HALT for ALL ambiguous tasks (any HALT trigger) |
| `maintenance` | HALT for ALL ambiguous tasks + any non-trivial change |

### HALT in Sub-Agent Prompts

When launching sub-agents, the orchestrator MUST include:

```
## HALT Protocol
If your task matches any HALT trigger (multi-service, data migration, API contract change,
auth/security modification), you MUST:
1. Output your PLAN with scope and risk assessment
2. Output "HALT: Waiting for approval before executing"
3. STOP and wait — do NOT proceed until approved

Current phase: {phase} — HALT scope: {phase-specific scope from table above}
```

### HALT vs Escalation

- **HALT**: Agent knows what to do but needs permission (ambiguity/risk)
- **Escalation**: Agent does NOT know what to do (failure/blocked)

HALT is proactive (before action). Escalation is reactive (after failed attempts).

## Integration with Existing Systems

### Error Learning
Every failed attempt is logged to error-learning.jsonl. After 3+ failures of the same pattern across sessions, the error-pattern-detector injects a warning.

### Skill Adaptation
If a skill consistently fails at the verification step, it accumulates feedback in Engram. After 3+ failures, skill rewrite is suggested.

### PITER Framework
Closed-loop prompts are the execution mechanism for the PITER Evaluate+Refine steps. The verification command IS the evaluation; the retry loop IS the refinement.

### ADW Pipelines
ADW steps with `on_failure: retry` use closed-loop prompts automatically. The `max_retries` field in the pipeline YAML maps to the attempt limit.

## Configuration

In `cognitive-os.yaml`:

```yaml
closed_loop:
  default_max_attempts: 3
  require_verification: true        # All agent prompts must include verification
  require_success_criteria: true     # All agent prompts must include criteria
  escalation_on_same_error: true     # Stop if same error repeats
  log_all_attempts: true             # Log each attempt to error-learning
```

## Examples

### Good: Concrete and Verifiable

```
## Success Criteria
- [ ] New endpoint GET /api/orders/:id returns 200 with order data
- [ ] Unit test for CreateOrder use case passes
- [ ] No lint errors in new files

## Verification
yarn test --filter="CreateOrder"
yarn lint src/orders/
curl -s localhost:3001/api/orders/test-id | jq .status
```

### Bad: Vague and Unverifiable

```
## Success Criteria
- [ ] Code works correctly
- [ ] Tests pass
- [ ] Code is clean
```

The first example lets the agent objectively verify; the second requires subjective judgment.

## Rule: Always Active

This rule applies to ALL sub-agent launches. The orchestrator MUST include success criteria and verification in every delegation prompt. If a skill does not define verification commands, the orchestrator should add appropriate ones based on the task type:

| Task Type | Default Verification |
|-----------|---------------------|
| Code change | `test` + `lint` + `build` |
| Configuration change | Service restart + health check |
| Documentation | File exists + not empty |
| Bug fix | Regression test passes + original error no longer occurs |
| Refactor | All existing tests still pass + no new lint errors |
