---
name: retrospective
version: 1.0.0
command: /retrospective
description: Weekly analysis of all squads with trend analysis and auto-reconfiguration proposals
last-updated: 2026-03-22
---

# Retrospective Skill

## Purpose

Run a comprehensive weekly analysis across all squads. Compare performance trends, identify patterns, and propose system-wide improvements. This is the organizational learning loop.

## Invocation

```
/retrospective [--scope organization|squad-name] [--period 7d|14d|30d]
```

- Default scope: `organization` (all squads)
- Default period: `7d` (last 7 days)

## Procedure

### Step 1: Collect Historical Data

1. **Current metrics**: Run `/squad-report` logic to get current snapshot
2. **Previous snapshots**: Search Engram for prior reports:
   ```
   mem_search(query: "squad-metrics/report", project: "{project}")
   ```
3. **Previous retrospectives**: Search for trend data:
   ```
   mem_search(query: "retrospective", project: "{project}")
   ```
4. **Error patterns**: Read `.claude/metrics/error-learning.jsonl` for the period
5. **Skill usage**: Read `.claude/metrics/skill-metrics.jsonl` for the period

### Step 2: Cross-Squad Comparison

Build a comparison matrix:

| Squad | Performance | Velocity | Cost | Coverage | Errors | Trend |
|-------|-------------|----------|------|----------|--------|-------|
| payments-team | {score} | {vel} | ${cost} | {cov}% | {errs} | {direction} |
| platform-team | {score} | {vel} | ${cost} | {cov}% | {errs} | {direction} |
| mobile-team | {score} | {vel} | ${cost} | {cov}% | {errs} | {direction} |
| infra-team | {score} | {vel} | ${cost} | {cov}% | {errs} | {direction} |

Identify:
- **Best performing squad** (highest composite score)
- **Most improved squad** (largest positive delta vs last period)
- **Squad needing attention** (lowest score or negative trend)

### Step 3: Trend Analysis

For each metric, calculate:
- **Direction**: improving, stable, degrading
- **Velocity**: rate of change per week
- **Projection**: estimated value in 2 weeks if trend continues

Flag any metric projected to breach its threshold within 2 weeks (early warning).

### Step 4: Error Pattern Analysis

Group errors from error-learning.jsonl by:
1. **Squad** (via repo ownership)
2. **Error type** (TEST_FAILURE, LINT_ERROR, BUILD_ERROR, etc.)
3. **Recurrence** (same error appearing multiple times)

Identify:
- Error types concentrating in specific squads
- Recurring errors that suggest skill gaps
- New error categories not seen before

### Step 5: Skill Usage Analysis

From skill-metrics.jsonl:
- Which skills are used most frequently
- Which skills have highest failure rates
- Which skills cost the most per invocation
- Skills not used at all (potential dead weight)

### Step 6: Cost Distribution

Calculate:
- Total cost per squad
- Cost per task per squad
- Model usage distribution (opus vs sonnet vs haiku)
- Budget burn rate vs organization limit

If projected monthly spend exceeds budgetLimit:
- Identify highest-cost squads
- Propose model downgrades for non-critical agents

### Step 7: Generate Auto-Reconfiguration Proposals

Based on analysis, propose reconfigurations:

| Condition | Action | Scope |
|-----------|--------|-------|
| Squad performance < 0.80 | upgradeModel for underperforming agents | Squad |
| Error recurrence > 0 for same type | skillUpdate -- regenerate affected skills | Squad |
| Cost per task > $2.00 | modelRotation -- downgrade non-critical agents | Organization |
| Squad improving after reconfig | documentSuccess -- save pattern to Engram | Organization |
| Skill failure rate > 20% | skillRetrain -- run /skill-creator | Skill |

### Step 8: Generate Report

Output format:

```markdown
# Retrospective Report — Week of {date}

## Executive Summary
{2-3 sentences: overall org health, key wins, key concerns}

## Organization Health
- Composite Score: {score}/100 ({trend})
- Budget: ${spent} / ${limit} ({burn_rate}/month projected)
- Active Squads: {N}
- Total Tasks Completed: {N}
- Total Errors: {N}

## Squad Rankings
| Rank | Squad | Score | Trend | Key Metric |
|------|-------|-------|-------|------------|
| 1 | {best} | {score} | {trend} | {notable} |
| 2 | ... | ... | ... | ... |

## Trend Analysis
### Improving
- {metric}: {from} -> {to} ({squad})

### Stable
- {metric}: {value} ({squad})

### Degrading (Action Required)
- {metric}: {from} -> {to} ({squad}) -- Proposed action: {action}

## Error Patterns
### By Squad
| Squad | Errors | Recurring | New |
|-------|--------|-----------|-----|
| ... | ... | ... | ... |

### Recurring Errors (need skill updates)
- {error type} in {squad}: {count} occurrences -- {root cause}

## Cost Analysis
| Squad | Total Cost | Cost/Task | Model Mix |
|-------|-----------|-----------|-----------|
| ... | ... | ... | opus:{N}% sonnet:{N}% haiku:{N}% |

## Skill Health
| Skill | Usage | Success Rate | Avg Cost | Recommendation |
|-------|-------|-------------|----------|----------------|
| ... | ... | ... | ... | {keep/retrain/deprecate} |

## Reconfiguration Proposals
1. **{action}** for {squad}: {reason} -- Expected impact: {impact}
2. ...

## Previous Reconfigurations (effectiveness)
| Date | Squad | Action | Result |
|------|-------|--------|--------|
| ... | ... | ... | {improved/no change/degraded} |

## Action Items
- [ ] {highest priority action}
- [ ] {second priority}
- [ ] ...
```

### Step 9: Persist Results

Save retrospective to Engram:

```
mem_save(
  title: "Retrospective {date}: {summary}",
  type: "pattern",
  project: "{project}",
  topic_key: "retrospective/{YYYY-MM-DD}",
  content: {full report}
)
```

Save per-squad snapshots:

```
FOR EACH squad:
  mem_save(
    title: "Squad metrics: {squad-name} {date}",
    type: "pattern",
    project: "{project}",
    topic_key: "squad-metrics/{squad-name}/{YYYY-MM-DD}",
    content: {squad section of report}
  )
```

## Output

Return:
- `status`: success | partial | error
- `executive_summary`: 2-3 sentence org health summary
- `squad_rankings`: ordered list of squads by performance
- `proposals`: list of reconfiguration proposals
- `action_items`: prioritized list of actions
- `next_recommended`: next retrospective date

## Notes

- First retrospective will have no historical data for trends -- this is expected
- If metrics files are empty, generate a "baseline" report noting the gaps
- Reconfigurations are PROPOSALS -- they require human approval
- The retrospective should take no more than 2 minutes to generate
- Save enough detail to Engram that the next retrospective can compute trends
