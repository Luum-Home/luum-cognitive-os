<!-- SCOPE: both -->
---
name: planning-poker
version: 1.0.0
last-updated: 2026-03-27
auto-generated: false
tech: python
triggers:
  - estimation
  - complexity
  - planning poker
  - how big is this task
  - estimate effort
audience: project
---

# Planning Poker — Multi-Agent Complexity Estimation

## Purpose

Like human Planning Poker (Scrum), but 3 AI reasoning approaches independently estimate a task's complexity, then their estimates are compared and reconciled. This is the first implementation of Planning Poker for AI agents.

## Invoke

```
/planning-poker <task-description>
```

## When to Use

- Before starting any medium+ task to calibrate expectations
- Before `/sdd-new` to inform sprint planning
- When the team disagrees on task scope
- When a task's complexity is ambiguous

## Steps

### Step 1: Parse Task

Read the task description. Identify:
- What needs to change (features, fixes, refactors)
- Which services/files are likely affected
- External dependencies or integrations involved
- Risk factors (security, data, infrastructure)

### Step 2: Generate 3 Independent Estimates

Each estimate uses a different reasoning approach. All three are generated independently — do NOT let one influence another.

#### Estimate A: Fast/Surface (haiku-like reasoning)
- Count explicit file paths, endpoints, or components mentioned
- Quick complexity classification based on surface signals
- Optimistic hours estimate
- Focus: what is STATED in the task

#### Estimate B: Deep/Thorough (opus-like reasoning)
- Analyze dependencies and blast radius
- Consider edge cases, error handling, test coverage
- Include infrastructure and deployment concerns
- Focus: what is IMPLIED by the task

#### Estimate C: Conservative/Risk-Aware (adversarial reasoning)
- Assume worst case for unknowns
- Factor in integration complexity and coordination overhead
- Consider what could go wrong
- Focus: what could SURPRISE us about the task

### Step 3: Run Poker Round

Use `lib/planning_poker.py`:

```python
from lib.planning_poker import create_estimate, run_poker_round, format_poker_table

estimates = [
    create_estimate("fast", complexity, files, h_min, h_max, risk, reasoning, confidence),
    create_estimate("deep", complexity, files, h_min, h_max, risk, reasoning, confidence),
    create_estimate("conservative", complexity, files, h_min, h_max, risk, reasoning, confidence),
]

result = run_poker_round(task_description, estimates)
```

### Step 4: Analyze Divergence

If `result.divergence_score > 2.0`:
- Explain WHY the estimates differ
- Identify the specific assumptions causing disagreement
- Highlight which unknowns drive the spread

If `result.divergence_score > 3.0`:
- Flag for human decision
- Present each agent's reasoning side by side
- Recommend which estimate to use based on project phase

### Step 5: Output Results

Use `format_poker_table(result)` to display the formatted table.

Include:
- The 3 individual estimates with reasoning
- Divergence score and interpretation
- Consensus estimate with confidence
- Recommendation for next action

### Step 6: Save to Metrics

```python
from lib.planning_poker import save_poker_round
save_poker_round(result, ".cognitive-os/metrics/planning-poker.jsonl")
```

### Step 7: Integration Recommendations

Based on consensus complexity:
- **TRIVIAL/SMALL**: Proceed directly, no SDD needed
- **MEDIUM**: Suggest `/plan-feature` before implementation
- **LARGE**: Recommend `/sdd-new` for full pipeline
- **CRITICAL**: Recommend `/sdd-new` with security review and `/impact-analysis`

## Complexity Levels Reference

| Level | Signal | Files | Hours | DoD |
|-------|--------|-------|-------|-----|
| TRIVIAL | Single file, <20 lines | 1 | <1h | compile + lint |
| SMALL | 1-3 files, single service | 1-3 | 1-3h | + unit tests pass |
| MEDIUM | Multi-file, new feature | 4-10 | 3-8h | + tests added + coverage |
| LARGE | Multi-service, integration | 10-30 | 8-20h | + integration tests + review |
| CRITICAL | Security, payments, migration | 15+ | 15-40h | + security review + rollback |

## Post-Completion Calibration

After the task is complete, run accuracy tracking:

```python
from lib.planning_poker import calculate_accuracy

actual = {"files": actual_files, "hours": actual_hours, "complexity": "medium"}
accuracy = calculate_accuracy(consensus_estimate, actual)
```

This feeds into the calibration loop: estimate -> actual -> accuracy -> adjust future estimates.

## Output Format

```
## Planning Poker Results

**Task**: Add JWT authentication to the user service

| Agent | Complexity | Files | Hours | Risk | Confidence |
|-------|-----------|-------|-------|------|------------|
| fast | SMALL | 4 | 2-3h | low | 0.75 |
| deep | MEDIUM | 8 | 4-6h | medium | 0.85 |
| conservative | LARGE | 12 | 6-10h | high | 0.80 |

**Divergence**: 2.50x (MODERATE — discussion required)

**Consensus**: MEDIUM, 8 files, 4-7h, medium risk (confidence: 0.80)
**Reasoning**: Moderate divergence (2.5x) — confidence-weighted average across 3 agents.
```
