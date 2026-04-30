<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Agent KPI Protocol

## When to Calculate KPIs

- At the end of every session (before session summary)
- When the user asks about agent performance
- When `/agent-kpis` is invoked
- Weekly: compare against previous week's baseline

## Data Sources

| Source | Path | Content |
|--------|------|---------|
| Skill metrics | `.claude/metrics/skill-metrics.jsonl` | Execution data per skill invocation |
| Error learning | `.claude/metrics/error-learning.jsonl` | Error patterns and recurrence tracking |
| Task tracking | `.claude/tasks/active-tasks.json` | Task lifecycle: launch, completion, retries |
| Skill feedback | Engram: `skill-feedback/*` | User corrections and skill adaptations |
| Previous KPIs | Engram: `agent-kpis/latest` | Last KPI snapshot for trend comparison |
| Historical KPIs | Engram: `agent-kpis/{date}` | Dated snapshots for long-term trends |

## OKR Targets

| OKR | Target | Critical Threshold |
|-----|--------|-------------------|
| Agent Quality | >90% composite | <85% triggers alert |
| Agent Efficiency | -20% month-over-month | Increasing trend triggers alert |
| Self-Improvement | Measurable improvement weekly | Error recurrence >0 triggers alert |
| Developer Velocity | >3x vs manual | <2x triggers review |
| Security & Compliance | 0 violations | Any violation is CRITICAL |
| Resource Efficiency | >80% composite | <60% triggers alert |
| Escalation Health | 5-15% escalation rate | <5% (suppressed) or >20% (too frequent) triggers alert |

## How KPIs Drive Improvement

These are automatic responses — the agent should suggest them when thresholds are breached:

| Condition | Action |
|-----------|--------|
| Average trust score < 75 | Suggest running `/trust-audit` to analyze trust patterns |
| Trust accuracy < 80% | Agents overclaiming — tighten verification in prompts |
| Self-awareness rate < 90% | Agents not admitting uncertainties — reinforce mandatory self-doubt |
| First-attempt success < 85% | Suggest running `/error-analyzer` to identify failure patterns |
| Tokens/task increasing vs last report | Suggest running `/model-optimizer` to review model routing |
| Error recurrence > 0 | Skills need updating — suggest `/optimize-skill` for affected skills |
| Retry rate > 20% | Fault tolerance system needs tuning — review `.claude/rules/fault-tolerance.md` |
| Gate violations > 0 | CRITICAL: Stop work, investigate immediately, report to user |
| Context efficiency > 50% | Delegation is insufficient — suggest breaking tasks into smaller sub-agents |
| User correction rate > 20% | Skill quality is degraded — run skill adaptation protocol |
| Resource efficiency < 80% | Run `/resource-governor` for optimization recommendations |
| Budget health < 20% | CRITICAL: Trigger model downgrade chain, alert user |
| Token efficiency < 80% | Run `/context-optimizer` to reduce wasted tokens |
| Infra utilization < 50% | Suggest stopping idle Docker containers |
| Escalation rate < 5% | Agents may be suppressing escalations — review agent preamble, ensure escalation protocol is loaded |
| Escalation rate > 20% | Too many escalations — review task clarity, acceptance criteria quality, or agent capability matching |
| Escalation resolution rate < 80% | Orchestrator failing to resolve escalations — review re-launch strategies |
| Time-to-escalate > 20 tool calls | Agents spinning too long before escalating — lower escalation thresholds |
| False escalation rate > 10% | Agents escalating unnecessarily — tighten detection thresholds |

### Resource Efficiency (NEW — from Resource Governor)

4 KPIs feed into the Resource Efficiency OKR:

| KPI | What it measures | Target | Data Source |
|-----|-----------------|--------|-------------|
| Token Efficiency | Tokens used productively vs total consumed | > 80% | `.cognitive-os/metrics/skill-metrics.jsonl` |
| Infra Utilization | Active Docker containers vs running containers | > 50% | `.cognitive-os/metrics/infra-usage.jsonl` + `docker ps` |
| Agent Efficiency | Successful agent completions vs total launches | > 80% | `.cognitive-os/metrics/skill-metrics.jsonl` |
| Budget Health | Remaining budget as % of monthly limit | > 20% remaining | `.cognitive-os/metrics/cost-events.jsonl` |

**Composite score**: weighted average of all 4 KPIs (equal weight 25% each).

**How to calculate**:
- Token Efficiency = sum(tokens where success=true) / sum(all tokens) * 100
- Infra Utilization = containers with recent activity / total running containers * 100
- Agent Efficiency = count(success=true) / count(all) * 100
- Budget Health = (1 - monthly_spend / monthly_limit) * 100

**Alert thresholds**:
- Composite < 80%: suggest running `/resource-governor`
- Budget Health < 20%: CRITICAL — suggest model downgrade
- Any single KPI < 50%: WARN — include in session summary

**Remediation**:
- Token waste detected: run `/context-optimizer`
- Low infra utilization: suggest stopping idle containers
- Low agent efficiency: review failing skills, reduce parallelism
- Budget pressure: trigger model downgrade chain (opus -> sonnet -> haiku)

### Trust Score

3 KPIs feed into agent trustworthiness measurement:

| KPI | What it measures | Target | Data Source |
|-----|-----------------|--------|-------------|
| Average Trust Score | Mean trust score across all agent completions | > 75 | `.cognitive-os/metrics/trust-scores.jsonl` |
| Trust Accuracy | How often high-trust results (score >= 80) are actually correct (no subsequent errors) | > 80% | Cross-reference `trust-scores.jsonl` with `error-learning.jsonl` |
| Self-Awareness Rate | % of agent completions that include uncertainty acknowledgments | 100% | `.cognitive-os/metrics/trust-scores.jsonl` |

**How to calculate**:
- Average Trust Score = sum(all scores) / count(all scores)
- Trust Accuracy = count(high-trust results with no follow-up errors) / count(high-trust results) * 100
- Self-Awareness Rate = count(reports with uncertainties > 0) / count(all reports) * 100

**Alert thresholds**:
- Average Trust Score < 75: suggest running `/trust-audit`
- Trust Accuracy < 80%: WARN — agents may be overclaiming confidence
- Self-Awareness Rate < 90%: WARN — agents not admitting uncertainties

**Remediation**:
- Low trust scores: review agent prompts, ensure acceptance criteria are included
- Low trust accuracy: tighten verification requirements, add more auto-verify checks
- Low self-awareness: reinforce mandatory self-doubt in agent prompts

### Architecture Compliance
- **What it measures**: % of services following the project's declared architecture patterns (per `cognitive-os.yaml -> project.architecture`)
- **How to calculate**: Count services using the declared framework vs non-standard alternatives, DTOs in correct layer (application/dtos/), proper source root usage
- **Target**: 100%
- **Alert threshold**: <90%
- **Data source**: `.claude/metrics/architecture-violations.jsonl`
- **Remediation**: Launch architecture remediation agent. In reconstruction phase, violations are blockers.

### Escalation Health

4 KPIs feed into escalation health measurement:

| KPI | What it measures | Target | Data Source |
|-----|-----------------|--------|-------------|
| Escalation Rate | Escalations / total agent completions | 5-15% | `.cognitive-os/metrics/escalation-events.jsonl` |
| Escalation Resolution Rate | Escalations resolved by orchestrator (re-launch succeeded) / total escalations | > 80% | Cross-reference `escalation-events.jsonl` with task completion |
| Time-to-Escalate | Average tool calls before escalating when stuck | < 15 tool calls | `.cognitive-os/metrics/escalation-events.jsonl` (stuck_duration field) |
| False Escalation Rate | Unnecessary escalations (task succeeded on immediate re-launch without changes) / total escalations | < 10% | `.cognitive-os/metrics/escalation-events.jsonl` cross-referenced with re-launch results |

**How to calculate**:
- Escalation Rate = count(escalation events) / count(agent completions) * 100
- Resolution Rate = count(escalations where re-launch succeeded) / count(all escalations) * 100
- Time-to-Escalate = mean(tool_calls_total from escalation events where escalation_count > 0)
- False Escalation Rate = count(escalations where immediate re-launch succeeds unchanged) / count(all escalations) * 100

**Alert thresholds**:
- Escalation rate < 5%: WARN -- agents may be suppressing escalations (spinning instead of asking for help)
- Escalation rate > 20%: WARN -- tasks may be too ambiguous or agents under-capable
- Resolution rate < 80%: WARN -- orchestrator strategies need improvement
- Time-to-escalate > 20: WARN -- agents spinning too long, lower detection thresholds
- False escalation rate > 10%: WARN -- detection is too sensitive

**Remediation**:
- Low escalation rate: review agent preamble for escalation instructions, verify escalation detector is active
- High escalation rate: improve task clarity, use `/exhaustive-prompt`, check model capability
- Low resolution rate: review orchestrator re-launch strategies, consider different models or approaches
- High time-to-escalate: lower `max_tool_calls_before_check` in EscalationDetector config
- High false escalation rate: raise thresholds in `lib/escalation_detector.py` constants

## KPI Storage

- **Current KPIs**: saved to Engram with topic_key `agent-kpis/latest` (upserted each run)
- **Historical snapshots**: saved with topic_key `agent-kpis/{YYYY-MM-DD}` (one per day)
- **Trend analysis**: compare last 5 snapshots when generating the dashboard

## Session-End Integration

Before calling `mem_session_summary`, the orchestrator should:

1. Check if enough data exists in `.claude/metrics/skill-metrics.jsonl` (at least 5 entries since last report)
2. If yes, run `/agent-kpis` to generate the dashboard
3. Include the OKR composite scores in the session summary under "## Agent Health"
4. If any CRITICAL alerts exist, highlight them at the top of the session summary

## Weekly Review Protocol

Every Monday (or when the user asks for a weekly review):

1. Retrieve the last 5 daily snapshots from Engram: `agent-kpis/{date}`
2. Calculate week-over-week trends for each OKR
3. Identify the KPI with the largest regression
4. Identify the KPI with the largest improvement
5. Generate a "Weekly Agent Health Report" with actionable recommendations
6. Save to Engram with topic_key `agent-kpis/weekly/{YYYY-Www}` (ISO week format)
