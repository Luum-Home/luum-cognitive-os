---
name: agent-kpis
description: Calculate and report Cognitive OS KPIs and OKRs. Shows agent health, efficiency, quality metrics. Use periodically or when evaluating agent performance.
user-invocable: true
version: 1.0.0
last-updated: 2026-03-21
audience: both
---

# Agent KPI Dashboard

Calculate, display, and track Cognitive OS performance metrics across 5 OKR categories.

## Instructions

### Step 1: Gather Data

1. Read `.claude/metrics/skill-metrics.jsonl` — each line is a JSON object with: `timestamp`, `skill`, `model`, `tokens`, `duration_ms`, `success`
2. Read `.claude/metrics/error-learning.jsonl` (if exists) — each line: `timestamp`, `error_type`, `pattern`, `resolution`, `recurred`
3. Read `.claude/tasks/active-tasks.json` — structured task list with `id`, `description`, `status`, `launchedAt`, `completedAt`, `outputSummary`
4. Search Engram for skill feedback: `mem_search(query: "skill-feedback", project: "{project}")`
5. Search Engram for previous KPI report: `mem_search(query: "agent-kpis/latest", project: "{project}")`

If a data file does not exist or is empty, note it as "no data" for that category and use 0/N/A for affected KPIs.

### Step 2: Calculate KPIs

#### OKR 1: Agent Quality (target: >90%)

| KPI | ID | Calculation | Source |
|-----|----|-------------|--------|
| First-attempt success rate | 1.1 | `(tasks with success=true on first run) / (total tasks)` * 100 | skill-metrics.jsonl |
| Test pass rate | 1.2 | `(test runs with success=true) / (total test runs)` * 100. Filter skill-metrics for skill="test" or skill="run" entries | skill-metrics.jsonl |
| Lint pass rate | 1.3 | `(lint runs with success=true) / (total lint runs)` * 100. Filter for skill="lint" | skill-metrics.jsonl |
| Build success rate | 1.4 | `(build runs with success=true) / (total build runs)` * 100. Filter for skill="build" | skill-metrics.jsonl |
| User correction rate | 1.5 | `(skill-feedback observations with type="correction") / (total tasks)` * 100. Lower is better. | Engram skill-feedback |

Composite score: weighted average — 1.1 (30%), 1.2 (25%), 1.3 (15%), 1.4 (15%), 1.5 (15% inverted: 100 - rate).

#### OKR 2: Agent Efficiency (target: reduce 20% month-over-month)

| KPI | ID | Calculation | Source |
|-----|----|-------------|--------|
| Tokens per task | 2.1 | `sum(tokens) / count(tasks)` for tasks with tokens > 0 | skill-metrics.jsonl |
| Time per task | 2.2 | `sum(duration_ms) / count(tasks)` converted to minutes | skill-metrics.jsonl |
| Cost per task | 2.3 | tokens * model pricing. Default: $3/M input + $15/M output for Opus, $0.80/$4 for Sonnet, $0.25/$1.25 for Haiku. Estimate 70% input / 30% output ratio. | skill-metrics.jsonl |
| Retry rate | 2.4 | `(tasks retried) / (total tasks)` * 100. A task is "retried" if the same description appears more than once in active-tasks. | active-tasks.json |
| Context efficiency | 2.5 | `avg(tokens per task) / 200000` * 100 (% of 200K context used). Lower is better. | skill-metrics.jsonl |

Trend: compare current period average vs previous report (from Engram).

#### OKR 3: Self-Improvement (target: measurable improvement each week)

| KPI | ID | Calculation | Source |
|-----|----|-------------|--------|
| Error pattern recurrence | 3.1 | Count entries in error-learning.jsonl where `recurred=true`. Should trend toward 0. | error-learning.jsonl |
| Skill adaptation count | 3.2 | Count Engram observations matching "skill-feedback" with type="pattern" (indicating skill was improved). | Engram |
| Model routing accuracy | 3.3 | `(tasks where model matched recommended model for skill category) / (total tasks with model data)` * 100. Cross-reference with `.claude/rules/model-routing.md` if exists. | skill-metrics.jsonl + rules |
| Recovery success rate | 3.4 | `(tasks with status="completed" that previously had status="failed" or "crashed") / (total failed tasks)` * 100 | active-tasks.json |

#### OKR 4: Developer Velocity (target: >3x vs manual)

| KPI | ID | Calculation | Source |
|-----|----|-------------|--------|
| Tasks completed per session | 4.1 | `count(completed tasks)` grouped by session (day). | active-tasks.json |
| Parallel agent utilization | 4.2 | Detect overlapping `launchedAt` windows (tasks running concurrently). Avg concurrent count. | active-tasks.json |
| Time-to-PR | 4.3 | For tasks with "PR" in description or outputSummary, measure `completedAt - launchedAt`. | active-tasks.json |
| Test coverage delta | 4.4 | Search Engram for "test coverage" observations. Report net change. If no data, report N/A. | Engram |

#### OKR 5: Security and Compliance (target: 0 violations)

| KPI | ID | Calculation | Source |
|-----|----|-------------|--------|
| Constitutional gate violations | 5.1 | Search Engram for "gate violation" or "constitutional". Count incidents. | Engram |
| License violations detected | 5.2 | Search Engram for "license violation" or "blocked license". Count incidents. | Engram |
| Production URL access attempts | 5.3 | Search Engram for "block-prod-urls" or "production URL". Count occurrences. | Engram |
| Secrets exposure incidents | 5.4 | Search Engram for "secrets exposure" or "sensitive data detected". Count. | Engram |

Composite score: 100% if all counts are 0. Deduct 25% per violation category with count > 0.

### Step 3: Generate Dashboard

Render the dashboard using this exact format (adjust values to calculated data):

```
+--------------------------------------------------------------+
|                  COGNITIVE OS KPI DASHBOARD                  |
|                    Period: {YYYY-MM-DD}                      |
+--------------------------------------------------------------+
|                                                              |
|  OKR 1: AGENT QUALITY                      Score: {X}%      |
|  +-- First-attempt success rate     {bar}  {X}%             |
|  +-- Test pass rate                 {bar}  {X}%             |
|  +-- Lint pass rate                 {bar}  {X}%             |
|  +-- Build success rate             {bar}  {X}%             |
|  +-- User correction rate           {bar}  {X}% (lower=better)|
|                                                              |
|  OKR 2: AGENT EFFICIENCY              Trend: {+/-X}% vs last|
|  +-- Avg tokens/task                {N} tokens              |
|  +-- Avg time/task                  {N} minutes             |
|  +-- Avg cost/task                  ${N}                    |
|  +-- Retry rate                     {bar}  {X}%             |
|  +-- Context efficiency             {bar}  {X}% used        |
|                                                              |
|  OKR 3: SELF-IMPROVEMENT                                     |
|  +-- Error recurrence               {bar}  {N} patterns     |
|  +-- Skills improved                {bar}  {N} this week    |
|  +-- Model routing accuracy         {bar}  {X}%             |
|  +-- Recovery success rate          {bar}  {X}%             |
|                                                              |
|  OKR 4: DEVELOPER VELOCITY                                   |
|  +-- Tasks/session                  {N} avg                 |
|  +-- Parallel agents                {N} avg concurrent      |
|  +-- Time-to-PR                     {N} min avg             |
|  +-- Test coverage delta            {+/-X}% this session    |
|                                                              |
|  OKR 5: SECURITY & COMPLIANCE              Score: {X}%      |
|  +-- Gate violations                {N}                     |
|  +-- License violations             {N}                     |
|  +-- Prod URL blocked               {N} (working as intended)|
|  +-- Secrets exposure               {N}                     |
|                                                              |
|  ALERTS:                                                     |
|  {list alerts based on thresholds below}                     |
|                                                              |
+--------------------------------------------------------------+
```

Bar format: use filled/empty blocks proportional to percentage (10-char bar).
- 0-10% = `#---------`
- 50% = `#####-----`
- 100% = `##########`

### Step 4: Generate Alerts

Apply these thresholds:

| Condition | Alert |
|-----------|-------|
| OKR 1 composite < 85% | "Agent quality below 85% target" |
| KPI 1.1 < 85% | "First-attempt success below 85% target" |
| KPI 1.5 > 20% | "User correction rate above 20% — review skill outputs" |
| KPI 2.4 > 20% | "Retry rate above 20% — tune fault tolerance" |
| KPI 2.5 > 50% | "Context usage above 50% — improve delegation" |
| KPI 3.1 > 0 | "{N} error patterns recurring — run /error-analyzer" |
| OKR 5 < 100% | "CRITICAL: Security violations detected — investigate immediately" |
| Any KPI has no data | "No data for {KPI name} — ensure metrics collection is active" |

### Step 5: Compare with Previous Report

1. Retrieve previous report from Engram: `mem_search(query: "agent-kpis/latest", project: "{project}")`
2. If found, use `mem_get_observation(id: ...)` to get full content
3. Compare each OKR composite score and highlight:
   - Improvements (arrow up + description)
   - Regressions (arrow down + description of what worsened)
   - Stable (dash + no change)
4. Add a "TRENDS" section after ALERTS showing the comparison

### Step 6: Save Report

Save the full dashboard output and raw KPI values to Engram:

```
mem_save(
  title: "Agent KPI Report {YYYY-MM-DD}",
  type: "discovery",
  project: "{project}",
  topic_key: "agent-kpis/latest",
  content: "{full dashboard output + raw values as structured data}"
)
```

Also save a historical snapshot:

```
mem_save(
  title: "Agent KPI Snapshot {YYYY-MM-DD}",
  type: "discovery",
  project: "{project}",
  topic_key: "agent-kpis/{YYYY-MM-DD}",
  content: "{raw KPI values only, for trend analysis}"
)
```

### Step 7: Recommend Actions

Based on the alerts, suggest concrete next steps:

| Alert | Recommendation |
|-------|---------------|
| Quality below target | Run `/error-analyzer` to identify failure patterns |
| Efficiency worsening | Run `/model-optimizer` to review model routing |
| Error recurrence | Update affected skills with `/optimize-skill` |
| High retry rate | Review fault tolerance config in `.claude/rules/fault-tolerance.md` |
| Security violations | Stop all work. Investigate the violation. Report to user. |
| Missing data | Verify hooks are installed: check `.claude/hooks/` for metrics collectors |
