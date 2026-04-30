<!-- SCOPE: both -->
---
name: model-optimizer
version: 1.0.0
last-updated: 2026-03-21
description: Analyze skill execution metrics and recommend optimal model routing
auto-generated: false
audience: both
platforms: ["claude-code"]
prerequisites: []
---

# Model Optimizer

Analyze collected skill metrics and generate model routing recommendations.

## Trigger

User runs `/model-optimizer`

## Instructions

You are the model optimizer. Your job is to read skill execution metrics, analyze them, and produce an updated model routing table.

### Step 1: Read Metrics

Read the file `.claude/metrics/skill-metrics.jsonl`. Each line is a JSON object with:
- `timestamp`: ISO 8601 timestamp
- `skill`: skill/agent name
- `model`: model used (opus, sonnet, haiku, unknown)
- `tokens`: total tokens consumed
- `duration_ms`: execution duration in milliseconds
- `success`: boolean indicating if the execution succeeded

If the file is empty or doesn't exist, report that there's no data yet and the default routing table remains in effect.

### Step 2: Group and Analyze

Group metrics by skill name. For each skill, calculate:

1. **Total executions**: count of entries
2. **Success rate**: successful / total (as percentage)
3. **Avg tokens**: average tokens per execution
4. **Avg duration**: average duration_ms per execution
5. **By model breakdown**: if a skill was run with different models, compare them

### Step 3: Score Models

For each skill-model combination with sufficient data (3+ executions), calculate a composite score:

```
score = quality × 0.4 + cost_efficiency × 0.3 + speed × 0.2 + success_rate × 0.1
```

Where:
- **quality**: Based on model tier: opus=1.0, sonnet=0.7, haiku=0.4
- **cost_efficiency**: Inverse of normalized token cost. Use these rates per 1M tokens:
  - opus: $15 input / $75 output (estimate $45 avg)
  - sonnet: $3 input / $15 output (estimate $9 avg)
  - haiku: $0.25 input / $1.25 output (estimate $0.75 avg)
  - Cost efficiency = 1 - (cost / max_cost) normalized to 0-1
- **speed**: Inverse of normalized duration. Faster = higher score
- **success_rate**: Direct percentage as 0-1

### Step 4: Generate Routing Table

Produce a markdown table with columns:
| Skill | Recommended Model | Confidence | Avg Cost | Notes |

Confidence levels:
- **high**: 10+ executions with clear winner (>20% score advantage)
- **medium**: 5-9 executions or close scores
- **low**: 3-4 executions
- **default**: fewer than 3 executions (keep initial guess)

### Step 5: Update Rule File

Write the updated routing table to `.claude/rules/model-routing.md`, preserving the file structure but replacing the table and updating the "Last updated" timestamp.

### Step 6: Save to Engram

Save the analysis summary to engram:
```
mem_save(
  title: "Model routing analysis",
  type: "decision",
  project: "{project}",
  topic_key: "model-routing/analysis",
  content: "**What**: Updated model routing based on {N} total executions across {M} skills\n**Why**: Periodic optimization of model selection for cost and performance\n**Where**: .claude/rules/model-routing.md\n**Learned**: {key findings}"
)
```

### Step 7: Report

Output a summary to the user:
- Total metrics analyzed
- Skills with enough data for recommendations
- Skills still on defaults
- Estimated monthly cost savings (if any model changes recommended)
- The updated routing table

## Output Format

```
## Model Routing Analysis

**Data range**: {earliest} to {latest}
**Total executions**: {N}
**Skills analyzed**: {M}

### Recommendations

{routing table}

### Key Findings
- {finding 1}
- {finding 2}

### Next Steps
- Skills needing more data: {list}
- Estimated savings: {amount or "insufficient data"}
```
