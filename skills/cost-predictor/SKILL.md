<!-- SCOPE: both -->
---
name: cost-predict
description: Predict task cost from Cognitive OS history, phase routing, and measured model prices.
summary_line: Estimate task cost from historical metrics and default phase routing.
version: 1.0.0
last-updated: 2026-04-23
auto-generated: false
tech: python
triggers:
  - cost predict
  - predict cost
  - estimate cost
  - budget forecast
  - how much will this cost
audience: project
platforms: ["claude-code"]
prerequisites: []
---

# Cost Predict

## Purpose

Give a real, bounded cost estimate before starting medium+ work. This skill uses the existing `lib/cost_predictor.py` engine and the metrics already written by Cognitive OS, so the output is grounded in project history rather than a generic guess.

## Invoke

```bash
/cost-predict <task-description>
```

## When to Use

- Before starting a medium, large, or critical task
- When deciding whether to split work into smaller slices
- When comparing implementation strategies with different likely costs
- When you need a budget forecast tied to real repository history

## Steps

### Step 1: Classify the task

Read the task description and choose the closest `task_type`:

- `feature`
- `bugfix`
- `refactor`
- `docs`
- `research`

If the task spans multiple types, choose the dominant cost driver and say so explicitly.

### Step 2: Run the predictor

Use the executable wrapper:

```bash
python3 scripts/cost_predict.py --type feature "Add codex-first settings projection to bootstrap"
```

If you need structured output for follow-on automation, use:

```bash
python3 scripts/cost_predict.py --json --type feature "Add codex-first settings projection to bootstrap"
```

### Step 3: Read the evidence

Interpret the result in this order:

1. Estimated range (`min`, `mid`, `max`)
2. Confidence level
3. Basis (`historical`, `model_routing`, `no_data`)
4. Similar tasks, if present
5. Recommendation

If the basis is `no_data` or confidence is low, say that clearly and treat the output as a planning hint, not a commitment.

### Step 4: Turn the estimate into a decision

- If cost is low and confidence is decent, proceed normally
- If cost is moderate or high, propose splitting the work
- If confidence is low, recommend a smaller exploratory slice first
- If the estimate is driven mostly by expensive phases, call that out

## Output Format

```text
## Cost Prediction

Task: Add codex-first settings projection to bootstrap
Task type: feature
Estimate: $0.42-$0.96 (mid: $0.63)
Confidence: MEDIUM (0.58)
Basis: historical
Recommendation: Most expensive phase: design (opus). Consider sonnet for non-reasoning phases.
```

## Contextual Trigger

Use this skill when the user asks how much a task will cost, asks for a budget forecast, or needs a quick estimate before implementation.
