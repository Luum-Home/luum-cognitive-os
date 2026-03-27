---
name: strands-evals-integration
description: >
  Configure Strands Evals for trace-based agent trajectory evaluation
  using OpenTelemetry instrumentation.
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-26
license: MIT
metadata:
  author: luum
  tool: strands-agents/evals
  tool-license: Apache-2.0
  tool-ring: TRIAL
  tool-score: 7.40
---

## Purpose

Strands Evals provides trace-based evaluation of agent trajectories using OpenTelemetry. It captures agent execution traces and evaluates them with built-in evaluators for tool selection accuracy, parameter correctness, and goal success.

## Invocation

`/strands-setup` — Initial configuration
`/strands-eval <trace>` — Evaluate an agent trace

## Setup

### Prerequisites
- Python 3.10+
- `pip install strands-agents-evals`

## What to Do

### Step 1: Instrument Agent Execution

Add OpenTelemetry tracing to agent execution:
```python
from strands_evals.telemetry import StrandsEvalsTelemetry

telemetry = StrandsEvalsTelemetry()
# Captures tool calls, LLM interactions, and decision points
```

### Step 2: Evaluate Trajectories

```python
from strands_evals.evaluators import (
    TrajectoryEvaluator,
    ToolSelectionAccuracyEvaluator,
    GoalSuccessRateEvaluator,
)

evaluator = TrajectoryEvaluator(
    evaluators=[
        ToolSelectionAccuracyEvaluator(),
        GoalSuccessRateEvaluator(),
    ]
)

results = evaluator.evaluate(agent_trace)
```

### Step 3: SDD Phase Validation

Define expected trajectories for SDD phases:
```python
expected_trajectory = [
    "sdd-propose", "sdd-spec", "sdd-design",
    "sdd-tasks", "sdd-apply", "sdd-verify"
]

# Evaluate actual trace against expected
accuracy = ToolSelectionAccuracyEvaluator().evaluate(
    actual=captured_trace,
    expected=expected_trajectory
)
```

## Rules

- Use for SDD phase trajectory validation and tool call sequence checks
- Complement with DeepEval for metric-level quality assessment
- OpenTelemetry traces stored in local collector, not cloud (cost control)
- TRIAL status — evaluate fit before committing to production use
