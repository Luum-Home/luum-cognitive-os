---
name: optimize-skill
description: Iteratively optimize a Claude Code skill with evaluations, score measurement, and prompt refinement.
user_invocable: true
disable-model-invocation: true
model: claude-opus-4-6
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent
audience: project
summary_line: Iteratively optimize a Claude Code skill with evaluations, score measurement, and prompt refinement.
version: 1.0.0
platforms:
- claude-code
prerequisites: []
triggers:
- optimize-skill
- /optimize-skill
- /optimize-skill — Karpathy Loop for Claude Code Skills
- iteratively optimize a Claude Code skill with evaluations
---
<!-- SCOPE: both -->
# /optimize-skill — Karpathy Loop for Claude Code Skills

## Arguments

```
/optimize-skill <skill-name> [iterations=3]
```

- `skill-name`: name of the skill to optimize (`check-health`, `start-stack`, etc.).
- `iterations`: number of optimization cycles to run (default: 3).

## Instructions

You are an autonomous skill optimizer inspired by Karpathy-style autoresearch.
Your goal is to improve the composite score of a skill without breaking behavior that already works.

### Step 1: Read the current state

```
Read:
  .claude/skills/{skill-name}/SKILL.md              → current skill
  .claude/skills/{skill-name}/evals/test-*.md       → test cases
  .claude/skills/{skill-name}/results/benchmark.tsv → history, if present
```

### Step 2: Run the baseline benchmark

For each evaluation in `evals/`:
1. Read the test case (input + expected behavior).
2. Mentally simulate executing the skill with that input.
3. Evaluate the result against the defined criteria.
4. Calculate metrics:
   - `pass_rate`: percentage of criteria that would pass.
   - `token_estimate`: estimated tokens used.
   - `tool_calls_estimate`: number of tool calls.
   - `quality`: 0-1 score based on expected format and completeness.

### Step 3: Identify improvement areas

Analyze the evaluations with the lowest scores and determine why:
- Are the instructions in `SKILL.md` ambiguous?
- Are there unnecessary steps that add tokens or time?
- Are concrete examples missing?
- Is the operation order suboptimal?
- Does the skill description fail to trigger correctly?

### Step 4: Propose one modification

Apply ONE modification to `SKILL.md` per iteration.
Use these strategies in priority order:
1. Correct instructions that cause evaluation failures.
2. Add examples for failing criteria.
3. Remove redundant steps to reduce tokens.
4. Reorder steps for efficiency.
5. Improve the description or name for triggering.
6. Simplify without losing precision.

### Step 5: Re-evaluate

Repeat Step 2 with the modified `SKILL.md`.
Compare scores.

### Step 6: Decide

```
IF new_score > previous_score:
  → Keep the change
  → Add a line to benchmark.tsv
  → Continue with the next iteration

IF new_score <= previous_score:
  → Revert SKILL.md to the previous state
  → Record in benchmark.tsv that the attempt failed
  → Try a different strategy
```

### Step 7: Final report

At the end of the iterations, show:

```
=== Skill Optimization Report: {skill-name} ===

Iterations: {N}
Initial score: {score_i}
Final score: {score_f}
Improvement: {delta} ({percentage}%)

Applied changes:
  1. {change description} → score: {x} → {y}
  2. ...

Discarded changes:
  1. {description} → did not improve (score: {x})

Final metrics:
  Pass rate: {%}
  Token efficiency: {%}
  Quality: {%}

Suggested next steps:
  - {suggestion 1}
  - {suggestion 2}
```

## Critical Rules

- NEVER modify files in `evals/`; they are the ground truth.
- ONLY modify the target skill's `SKILL.md`.
- Make ONE modification per iteration so the effect can be isolated.
- After 3 consecutive failed attempts, STOP and report.
- Each successful change must be explainable (no "magic").
