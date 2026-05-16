---
name: squad-manager
version: 1.0.0
command: /squad-report
description: Evaluate squad performance and propose reconfigurations
last-updated: 2026-03-22
audience: project
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bsquad[- ]?manager\b
  confidence: 0.95
- pattern: \bsquad\s+performance\b
  confidence: 0.85
- pattern: \breconfigur\w+\s+squad\b
  confidence: 0.75
routing_intents:
- evaluate current squad performance across active agent assignments
- recommend squad reconfiguration options from workload evidence
- generate a squad status report for active coordination work
- analyze which agents should be reassigned
- review squad composition and workload balance
triggers:
- squad-manager
- /squad-manager
- Squad Manager Skill
- Evaluate squad performance and propose reconfigurations
---
<!-- SCOPE: both -->
# Squad Manager Skill

## Purpose

Evaluate agent and squad performance metrics, generate a squad performance report, and propose reconfigurations when thresholds are breached.

## Invocation

```
/squad-report [squad-name]
```

- Without arguments: generates a report for ALL squads
- With squad name: generates a report for a specific squad (e.g., `/squad-report payments-team`)

## Procedure

### Step 1: Load Squad Configurations

Read squad YAML files from `.claude/squads/`:

```bash
ls .claude/squads/*.yaml
```

Parse `organization.yaml` for global governance settings.
Parse individual squad files for member lists, repos, skills, and metric targets.

### Step 2: Collect Agent Metrics

Read metrics from existing data sources:

1. **skill-metrics.jsonl** (`.claude/metrics/skill-metrics.jsonl`):
   - Extract per-agent: successRate, tokensUsed, costPerTask, duration
   - Filter to last 7 days for weekly report

2. **error-learning.jsonl** (`.claude/metrics/error-learning.jsonl`):
   - Extract per-service: error count, error types, recurrence
   - Map services to squads via repo ownership

3. **active-tasks.json** (`.claude/tasks/active-tasks.json`):
   - Extract: task completion rate, average resolution time, retry rate

### Step 3: Calculate Squad Metrics

For each squad, compute:

| Metric | Formula |
|--------|---------|
| squadPerformance | Weighted average of member successRates (manager weight: 0.3, others: equal) |
| coverageStatus | Current test coverage vs target from squad YAML |
| architectureCompliance | Constitutional gate violations / total changes |
| velocityTrend | Tasks completed this week vs 4-week rolling average |
| costEfficiency | Total cost this week / tasks completed |
| errorRate | Errors attributed to squad repos / total changes |

### Step 4: Evaluate Thresholds

Compare computed metrics against thresholds defined in squad YAML and organization YAML:

```
FOR EACH squad:
  FOR EACH metric IN squad.metrics.targets:
    IF current_value VIOLATES threshold:
      ADD to reconfiguration_proposals
```

### Step 5: Generate Reconfiguration Proposals

If thresholds are breached, propose actions based on the ManagerAgent's `autoReconfigure.triggers`:

| Condition | Proposal |
|-----------|----------|
| successRate < 0.80 | Upgrade model (sonnet -> opus) for underperforming agents |
| architectureCompliance < 0.90 | Retrain skills -- regenerate with latest patterns |
| issueResolutionTime > target | Scale up -- increase agent instances |
| bugsIntroduced > 3 | Add QA agent to squad |
| costPerTask > $2.00 | Rotate models -- downgrade non-critical agents |

Check cooldown: no reconfiguration if one was applied in the last 24h.

### Step 6: Generate Report

Output format:

```markdown
# Squad Performance Report — {date}

## Organization Summary
- Total squads: {N}
- Overall health: {composite score}
- Budget usage: ${spent} / ${limit} ({percentage}%)

## Squad: {squad-name}
### Health: {score}/100 {trend_emoji}

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Success Rate | {val} | {target} | {OK/WARN/CRIT} |
| Architecture Compliance | {val} | {target} | {OK/WARN/CRIT} |
| Coverage | {val}% | {target}% | {OK/WARN/CRIT} |
| Avg Resolution Time | {val}min | {target}min | {OK/WARN/CRIT} |
| Cost/Task | ${val} | ${target} | {OK/WARN/CRIT} |
| Error Rate | {val} | <5% | {OK/WARN/CRIT} |

### Top Agents
| Agent | Tasks | Success | Cost |
|-------|-------|---------|------|
| {name} | {N} | {rate}% | ${cost} |

### Issues
- {list of threshold breaches}

### Proposed Reconfigurations
- {list of proposals, if any}

(repeat for each squad)

## Cross-Squad Comparison
| Squad | Health | Velocity | Cost | Trend |
|-------|--------|----------|------|-------|
| payments-team | {score} | {vel} | ${cost} | {trend} |
| platform-team | {score} | {vel} | ${cost} | {trend} |
| ...

## Recommendations
1. {highest priority recommendation}
2. {second priority}
3. ...
```

### Step 7: Persist Results

Save the report to Engram:

```
mem_save(
  title: "Squad report {date}",
  type: "pattern",
  project: "{project}",
  topic_key: "squad-metrics/report/{YYYY-MM-DD}",
  content: {report summary -- key metrics and proposals only}
)
```

If reconfigurations are proposed:

```
mem_save(
  title: "Squad reconfig proposal: {squad-name}",
  type: "decision",
  project: "{project}",
  topic_key: "squad-reconfig/{squad-name}/{YYYY-MM-DD}",
  content: {proposal details}
)
```

## Output

Return:
- `status`: success | partial (if some data sources missing) | error
- `executive_summary`: 2-3 sentence summary of org health
- `squads`: per-squad health scores
- `proposals`: list of reconfiguration proposals (if any)
- `next_recommended`: when to run next report

## Notes

- If `.claude/metrics/skill-metrics.jsonl` does not exist or is empty, report with available data and note the gap
- If a squad has no recent activity, mark it as "inactive" rather than failing
- Reconfigurations are PROPOSALS only -- they require human approval before applying
- The manager agent (opus) evaluates proposals; operational agents (sonnet) execute them
