# PITER Framework — AFK Agent Autonomy

> Source: "Tactical Agentic Coding" by IndyDevDan (agenticengineer.com)

## What is PITER?

PITER is a five-step loop that enables agents to work **AFK (Away From Keyboard)** — without human supervision between steps.

```
Plan → Implement → Test → Evaluate → Refine
  ^                                      |
  +--------------------------------------+
         (automatic loop until done)
```

Each step has clear entry/exit criteria so the agent can decide autonomously whether to proceed or loop back.

## The Five Steps

### 1. Plan
- Understand the task requirements
- Break down into actionable steps
- Identify success criteria and verification methods
- Output: structured plan with acceptance criteria

### 2. Implement
- Execute the plan step by step
- Write code, modify configs, create files
- Follow architecture standards and conventions
- Output: working implementation

### 3. Test
- Run automated tests (unit, integration, e2e)
- Run linters and type checkers
- Verify the implementation against the plan
- Output: test results (pass/fail with details)

### 4. Evaluate
- Compare results against success criteria from step 1
- Check for regressions
- Assess code quality and standards compliance
- Output: evaluation report (pass/fail with gaps identified)

### 5. Refine
- If evaluation passed: done, exit loop
- If evaluation failed: analyze gaps, adjust approach, loop back to Plan or Implement
- Maximum refinement iterations: 3 (then escalate to human)
- Output: either "done" or adjusted plan for next iteration

## Mapping to Cognitive OS Components

| PITER Step | Cognitive OS Equivalent | Current State |
|------------|---------------------|---------------|
| Plan | SDD (sdd-propose, sdd-spec, sdd-design, sdd-tasks) | Implemented |
| Implement | sdd-apply, sub-agent delegation | Implemented |
| Test | auto-test-on-edit hook, test commands | Implemented |
| Evaluate | sdd-verify, verification-before-completion skill | Implemented |
| Refine | auto-refine hook + skill, closed-loop-prompts | Implemented |

## What We Have vs What PITER Adds

### Already Implemented
- Planning via SDD phases
- Implementation via sdd-apply
- Testing via hooks and manual commands
- Evaluation via sdd-verify
- Error learning for post-hoc improvement

### Automatic Refinement Loop (IMPLEMENTED)

The refinement gap is now closed. Agents auto-fix their work instead of stopping at evaluation:

```
Before:   Plan → Implement → Test → Evaluate → REPORT TO HUMAN (wait)
Now:      Plan → Implement → Test → Evaluate → Refine → (loop or done)
```

Implementation consists of:

1. **`auto-refine.sh` hook** (PostToolUse on Agent): Detects failures in agent output and outputs retry instructions for the orchestrator. Tracks retries per task (max 3). Phase-aware: auto-retry in reconstruction/stabilization, suggest-only in production/maintenance.

2. **Closed-loop prompt protocol** (`closed-loop-prompts.md`): Every agent prompt MUST include auto-refine instructions telling the agent to fix and retry up to 3 times.

3. **`/auto-refine` skill**: Manual or orchestrator-driven refinement with structured root cause analysis and re-launch.

4. **Refinement budget**: Max 3 iterations, tracked per task fingerprint in `.cognitive-os/metrics/auto-refine/`.

5. **Escalation criteria**: Stop looping when max retries reached, same error repeats, error requires architectural change, or test infrastructure is broken.

## PITER in ADW Pipelines

PITER can be embedded in any ADW pipeline as an inner loop:

```yaml
# Example: feature-pipeline with PITER
steps:
  - name: sdd-propose
  - name: sdd-spec
  - name: sdd-design
  - name: sdd-tasks
  - name: piter-loop          # <-- PITER wraps apply+verify
    config:
      max_iterations: 3
      plan: sdd-tasks output
      implement: sdd-apply
      test: run-tests
      evaluate: sdd-verify
      refine: auto-adjust
  - name: sdd-archive
```

## Implementation Priority

| Component | Priority | Effort | Dependency |
|-----------|----------|--------|------------|
| Closed-loop prompts rule | High | Low | None |
| Refinement budget in cognitive-os.yaml | Medium | Low | closed-loop-prompts |
| Gap analysis template | Medium | Low | None |
| PITER workflow wrapper | Low | Medium | ADW pipelines, closed-loop-prompts |

## Relationship to ZTE

PITER is a building block toward Zero-Touch Engineering (ZTE). Each PITER loop that succeeds without human intervention moves the system closer to full ZTE. See `zero-touch-engineering.md`.
