# ADW Patterns — AI Developer Workflows

> Source: "Tactical Agentic Coding" by IndyDevDan (agenticengineer.com)

## What is an ADW?

An AI Developer Workflow (ADW) combines **deterministic code** (pipelines, scripts, CI steps) with **non-deterministic agents** (LLM-powered decision-making and code generation). The deterministic layer provides structure and repeatability; the agent layer provides intelligence and adaptability.

```
ADW = Deterministic Pipeline + Non-Deterministic Agents
```

### Key Properties

- **Repeatable**: Same trigger produces consistent workflow structure
- **Measurable**: Each step has metrics (duration, cost, success rate)
- **Optimizable**: Metrics drive improvements to both pipeline and agent steps
- **Composable**: ADWs can embed other ADWs or share steps

## Cognitive OS as ADW Implementation

The `.cognitive-os/workflows/` directory IS an ADW implementation. Each workflow YAML defines a deterministic pipeline that orchestrates non-deterministic agent execution.

### Our ADW Pipelines

| Pipeline | File | Purpose | Steps |
|----------|------|---------|-------|
| Feature | `feature-pipeline.yaml` | New feature development | propose, spec, design, tasks, apply, verify, archive |
| Bug Fix | `bugfix-pipeline.yaml` | Bug investigation and fix | reproduce, diagnose, fix, test, verify |
| Refactor | `refactor-pipeline.yaml` | Code improvement | analyze, plan, apply, verify |
| SRE | `sre-pipeline.yaml` | Incident response | detect, classify, repair, verify, document |
| Review | `review-pipeline.yaml` | Code review automation | analyze, check-gates, report |

### Anatomy of an ADW Step

Each step in an ADW has:

```yaml
steps:
  - name: step-name
    type: agent | script | gate
    skill: skill-name              # Which skill the agent loads
    model: sonnet | opus | haiku   # Model routing
    inputs:                        # What this step receives
      - previous-step.output
    outputs:                       # What this step produces
      - artifact-key
    success_criteria:              # How to verify success
      - condition: "artifact exists"
      - condition: "tests pass"
    on_failure: retry | skip | abort | escalate
    max_retries: 3
```

### Step Types

| Type | Behavior | Example |
|------|----------|---------|
| `agent` | Sub-agent executes with skill loaded | sdd-apply, systematic-debugging |
| `script` | Deterministic command execution | `yarn test`, `go build` |
| `gate` | Boolean check, blocks pipeline if false | test coverage > 80%, no lint errors |

## ADW Lifecycle

### 1. Design

Define the pipeline steps, their dependencies, and success criteria.

```
Trigger → Step 1 → Gate → Step 2 → Step 3 → Gate → Output
                     |                         |
                     v                         v
                  (abort)                   (retry)
```

Questions to answer:
- What triggers this workflow?
- What are the mandatory steps vs optional?
- What gates prevent bad outputs from flowing downstream?
- What is the maximum budget (tokens, time, cost)?

### 2. Test

Validate the pipeline with controlled inputs before deploying.

- Run with a known task that has a known-good outcome
- Verify each step produces expected artifacts
- Verify gates correctly block bad inputs
- Measure baseline metrics (duration, cost, token usage)

### 3. Deploy

Make the pipeline available for use.

- Add to `.cognitive-os/workflows/`
- Register in cognitive-os.yaml under `workflows`
- Add entry to CATALOG.md if user-invocable
- Document trigger mechanism (command, event, schedule)

### 4. Monitor

Track pipeline performance over time.

- skill-metrics.jsonl captures per-step data
- Agent KPIs aggregate pipeline-level metrics
- Error learning captures step failures

### 5. Optimize

Improve based on monitoring data.

- Model routing: downgrade model for steps that succeed with cheaper models
- Step consolidation: merge steps that always run together
- Gate tuning: adjust thresholds based on false positive/negative rates
- Budget adjustment: tighten or loosen per-step budgets

## Creating a New ADW

### Step 1: Define the Workflow

```yaml
# .cognitive-os/workflows/my-workflow.yaml
name: my-workflow
description: What this workflow does
trigger: manual | event | schedule
budget:
  max_cost: $2.00
  max_duration: 30m
steps:
  - name: analyze
    type: agent
    skill: analysis-skill
    model: sonnet
    outputs: [analysis-report]
  - name: quality-gate
    type: gate
    condition: "analysis-report.confidence > 0.8"
    on_failure: abort
  - name: execute
    type: agent
    skill: execution-skill
    model: sonnet
    inputs: [analysis-report]
    outputs: [result]
    on_failure: retry
    max_retries: 2
```

### Step 2: Add PITER Loop (Optional)

For workflows that should self-correct:

```yaml
  - name: implement-and-verify
    type: piter-loop
    config:
      max_iterations: 3
      plan: analyze.output
      implement_skill: execution-skill
      test_command: "yarn test"
      evaluate_skill: verification-skill
```

### Step 3: Register

Add to `cognitive-os.yaml`:

```yaml
workflows:
  my-workflow:
    file: workflows/my-workflow.yaml
    trigger: manual
    command: /my-workflow
```

## ADW Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| All-agent pipeline | No deterministic checkpoints, unpredictable | Add gates between agent steps |
| No budget limits | Cost can spiral on complex tasks | Set max_cost and max_duration |
| Missing success criteria | Cannot verify step completed correctly | Every agent step needs verification |
| Monolithic steps | One step does too much, hard to debug | Break into smaller, focused steps |
| No failure handling | Pipeline crashes on first error | Define on_failure for each step |
| Hardcoded models | Cannot optimize cost/quality tradeoff | Use model-routing table |

## Relationship to Other Concepts

| Concept | Relationship |
|---------|-------------|
| PITER | PITER is an inner loop within ADW steps — it handles the implement/test/refine cycle |
| SDD | SDD is the most mature ADW in Cognitive OS — 8 phases with defined artifacts |
| Closed-loop prompts | Enable agent steps to self-correct within their execution |
| ZTE | ADWs are the execution mechanism for ZTE — event-triggered ADWs are Phase 2 |
| Leverage Point 10 | ADWs ARE leverage point 10 (workflow automation) |
