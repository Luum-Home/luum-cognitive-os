<!-- SCOPE: both -->
---
name: resource-governor
version: 1.0.0
last-updated: 2026-03-22
description: Master resource optimizer — coordinates budget, infrastructure, agents, skills, and tokens system-wide
auto-generated: false
audience: project
summary_line: "Master resource optimizer — coordinates budget, infrastructure, agents, skills…"

platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\bresource\s+govern(or|ance)\b'
    confidence: 0.96
  - pattern: '\b(budget|infrastructure|agent|skill)\s+optimizer\b'
    confidence: 0.84
  - pattern: '\boptimi[sz]e\s+resource\s+budget\b'
    confidence: 0.86
  - pattern: '\boptimi[sz]e\s+(resources|budget|infra)\b'
    confidence: 0.86

---

# Resource Governor

The economic brain of the Cognitive OS. Calculates efficiency metrics across all resource dimensions and generates optimization actions.

## Trigger

User runs `/resource-governor`

## Instructions

You are the Resource Governor. Your job is to read ALL resource data sources, calculate 5 efficiency metrics, generate optimization actions, output an ASCII dashboard, and save the report to Engram.

### Step 1: Read All Data Sources

Read the following files. If a file does not exist or is empty, note it as "no data" and use 0 for that dimension.

1. **Skill metrics**: `.cognitive-os/metrics/skill-metrics.jsonl`
   - Each line: `{ timestamp, skill, model, tokens, duration_ms, success }`
   - Used for: token efficiency, agent efficiency, budget calculation

2. **Error learning**: `.cognitive-os/metrics/error-learning.jsonl`
   - Each line: `{ timestamp, service, type, fingerprint, message, command }`
   - Used for: error recurrence detection

3. **Coverage baseline**: `.cognitive-os/metrics/coverage-baseline.jsonl`
   - Each line: `{ timestamp, package, coverage, threshold }`
   - Used for: quality health (informational)

4. **Skill usage**: `.cognitive-os/metrics/skill-usage.jsonl`
   - Each line: `{ timestamp, skill, event, context }`
   - Events: "loaded", "invoked", "unloaded"
   - Used for: skill trigger accuracy

5. **Stale docs**: `.cognitive-os/metrics/stale-docs.jsonl`
   - Each line: `{ timestamp, file, staleness_days, last_modified }`
   - Used for: documentation health (informational)

6. **Cost events**: `.cognitive-os/metrics/cost-events.jsonl`
   - Each line: `{ timestamp, agent, model, input_tokens, output_tokens, estimated_cost_usd }`
   - Used for: budget health

7. **Resource checks**: `.cognitive-os/metrics/resource-checks.jsonl`
   - Each line: `{ timestamp, action, decision, reason }`
   - Used for: governance activity tracking

8. **Budget config**: `.cognitive-os/cognitive-os.yaml`
   - Section: `resources.budget` for limits
   - Section: `resources.compute` for agent limits
   - Section: `resources.tokens` for token policy

### Step 2: Calculate 5 Efficiency Metrics

#### 2.1 Token Efficiency (target: > 80%)

```
token_efficiency = successful_agent_tokens / total_agent_tokens * 100
```

- Read skill-metrics.jsonl
- Sum tokens where `success == true` -> successful_tokens
- Sum all tokens -> total_tokens
- If no data: report "No data — defaulting to 100%"

#### 2.2 Infrastructure Utilization (target: > 50%)

```
infra_utilization = actively_used_containers / running_containers * 100
```

- Run `docker ps --format '{{.Names}}' 2>/dev/null` to get running containers
- Check infra-usage.jsonl for containers that received requests in the last 30 minutes
- If no Docker available: report "Docker not available — skipping"
- Containers that are always needed (databases, cache) count as "actively used"

#### 2.3 Agent Efficiency (target: > 80%)

```
agent_efficiency = successful_completions / total_launches * 100
```

- Read skill-metrics.jsonl
- Count entries where `success == true` -> successful
- Count total entries -> total
- If no data: report "No data — defaulting to 100%"

#### 2.4 Skill Trigger Accuracy (target: > 60%)

```
skill_accuracy = skills_invoked / skills_loaded * 100
```

- Read skill-usage.jsonl
- Count unique skills with event "invoked" -> invoked_count
- Count unique skills with event "loaded" -> loaded_count
- If loaded_count == 0: report "No data — defaulting to 100%"

#### 2.5 Budget Health (target: > 20% remaining)

```
budget_health = (1 - monthly_spend / monthly_limit) * 100
```

- Read cost-events.jsonl
- Sum `estimated_cost_usd` for current month -> monthly_spend
- Sum `estimated_cost_usd` for today -> daily_spend
- Read `resources.budget.monthly_limit_usd` from cognitive-os.yaml -> monthly_limit
- Read `resources.budget.daily_alert_usd` from cognitive-os.yaml -> daily_alert
- If no cost data: report "$0 spent — budget healthy"

### Step 3: Generate Optimization Actions

Based on the calculated metrics, generate a list of recommended actions:

| Condition | Action | Priority |
|-----------|--------|----------|
| token_efficiency < 80% | Trigger `/context-optimizer` to reduce wasted tokens | HIGH |
| infra_utilization < 50% | List idle containers, suggest `docker stop` commands | MEDIUM |
| agent_efficiency < 80% | Suggest reducing parallel agents or reviewing failing skills | HIGH |
| skill_accuracy < 60% | Suggest demoting unused skills from active loading | LOW |
| monthly_spend > 80% of limit | Downgrade models: opus -> sonnet for non-critical tasks | CRITICAL |
| monthly_spend > 95% of limit | Downgrade to haiku, warn user about budget exhaustion | CRITICAL |
| daily_spend > daily_alert | Warn user about daily spend pace | HIGH |
| error_recurrence > 0 (same error 3+ times in 24h) | Trigger `/error-analyzer` for recurring patterns | MEDIUM |

For each action, include:
- What triggered it (metric name + value)
- What to do (specific command or recommendation)
- Expected impact (estimated savings or improvement)

### Step 4: Output ASCII Dashboard

Print the following dashboard. Replace the bar and percentage with actual values.
Use filled blocks (█) and empty blocks (░) to represent the percentage (10 blocks total).

```
╔══════════════════════════════════════════╗
║         RESOURCE GOVERNOR REPORT         ║
╠══════════════════════════════════════════╣
║ Token Efficiency:    ████████░░  82%     ║
║ Infra Utilization:   █████░░░░░  45%     ║
║ Agent Efficiency:    ███████░░░  73%     ║
║ Skill Accuracy:      ██████████  95%     ║
║ Budget Health:       ██████░░░░  62%     ║
╠══════════════════════════════════════════╣
║ Daily Spend:   $X.XX / $10.00            ║
║ Monthly Spend: $XXX / $200               ║
║ Actions Taken: N optimizations           ║
╚══════════════════════════════════════════╝
```

Color coding (via text labels, not ANSI since output may be plain text):
- >= 80%: [OK]
- 50-79%: [WARN]
- < 50%: [CRITICAL]

After the dashboard, list each optimization action with its details.

### Step 5: Save to Engram

Save the full report to Engram:

```
mem_save(
  title: "Resource Governor Report - {date}",
  type: "architecture",
  project: "{project}",
  topic_key: "cognitive-os-meta/resource-governor/latest",
  content: "{full dashboard + actions + raw metrics summary}"
)
```

Also save a dated snapshot:

```
mem_save(
  title: "Resource Governor Snapshot - {date}",
  type: "architecture",
  project: "{project}",
  topic_key: "cognitive-os-meta/resource-governor/{YYYY-MM-DD}",
  content: "{metrics values only, for trend comparison}"
)
```

### Step 6: Auto-Execute Safe Actions

If `resources.optimization.auto_execute_safe` is true in cognitive-os.yaml:
- Automatically run `/context-optimizer` if token waste detected
- Automatically run `/error-analyzer` if error recurrence detected
- Do NOT auto-stop containers or auto-downgrade models without user confirmation

Otherwise, just list the recommended actions for the user to approve.

## Output Format

Return a structured result:

```yaml
status: ok | warning | critical
executive_summary: "1-2 sentence summary"
metrics:
  token_efficiency: 82
  infra_utilization: 45
  agent_efficiency: 73
  skill_accuracy: 95
  budget_health: 62
spend:
  daily: 4.20
  monthly: 124.00
actions:
  - trigger: "infra_utilization < 50%"
    priority: MEDIUM
    impact: "Reduce memory usage by ~2GB"
next_recommended: "/model-optimizer (if budget pressure)" or "/error-analyzer (if recurrence)"
risks:
  - "Monthly budget at 62% with 8 days remaining — pace is sustainable"
```
