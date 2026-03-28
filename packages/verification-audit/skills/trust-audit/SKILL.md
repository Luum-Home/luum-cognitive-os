---
name: trust-audit
description: Analyze trust scores across agents and tasks, identify patterns, recommend reviews
invoke: /trust-audit
tag: universal
model: sonnet
---

# Trust Audit Skill

## Purpose

Analyze accumulated trust scores to answer: which agents are trustworthy? Which overclaim? Which results need human review?

## Invocation

```
/trust-audit [--period=7d] [--agent=name] [--threshold=70]
```

## Input

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--period` | `7d` | Time window to analyze (7d, 30d, all) |
| `--agent` | all | Filter to specific agent name |
| `--threshold` | 70 | Flag scores below this value |

## Procedure

### 1. Load Data

Read `.cognitive-os/metrics/trust-scores.jsonl`. Each line:
```json
{"timestamp": "ISO-8601", "agent": "name", "score": 75, "task": "...", "components": {...}}
```

If file is empty or missing, report "No trust data collected yet."

### 2. Aggregate Metrics

For each agent (or overall if no filter):

- **Average trust score**: mean of all scores
- **Score distribution**: count per bracket (90-100, 70-89, 50-69, 0-49)
- **Consistency**: standard deviation of scores (low = consistent, high = erratic)
- **Uncertainty rate**: % of completions that included uncertainties (target: 100%)
- **Low-confidence count**: number of scores below threshold

### 3. Detect Overclaiming

Flag agents that consistently report high scores (avg > 85) but:
- Have low uncertainty rate (< 50% of reports include self-doubt)
- Have high retry rates (from skill-metrics.jsonl)
- Have error patterns (from error-learning.jsonl)

These are "overconfident" agents -- they claim high trust but evidence suggests otherwise.

### 4. Trend Analysis

Compare current period vs previous period:
- Is average trust improving or declining?
- Are low-confidence results decreasing?
- Are specific task types consistently low-trust?

### 5. Generate Report

```
TRUST AUDIT REPORT
Period: {start} to {end}
Total completions analyzed: {N}

OVERALL HEALTH:
  Average Trust Score: {avg}/100
  Distribution: {high}% high | {medium}% medium | {low}% low | {vlow}% very low

AGENT BREAKDOWN:
  {agent}: avg={score}, consistency={std_dev}, uncertainty_rate={pct}%
  ...

OVERCLAIMING ALERTS:
  {agent}: Claims avg {score} but has {error_count} errors and {retry_count} retries
  ...

RESULTS NEEDING HUMAN REVIEW:
  - [{score}/100] {task} by {agent} at {timestamp}
  ...

TREND:
  vs previous period: {improving/declining/stable} ({delta})

RECOMMENDATIONS:
  - {actionable recommendation}
  ...
```

## Output

The report above, plus:
- Save audit results to Engram with topic_key `agent/trust-audit/{date}`
- If average < 75: WARN "Trust scores below target. Review agent prompts and verification practices."

## Acceptance Criteria

1. `grep -c "TRUST AUDIT REPORT" output` >= 1
2. All agents with data appear in breakdown
3. Overclaiming detection runs (even if no alerts)
4. Recommendations are actionable (not generic)
