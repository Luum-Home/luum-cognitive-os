<!-- TIER: 2 -->
<!-- SCOPE: both -->
# Singularity Rule — Autonomous MAPE-K Control Loop

## Activation

The Singularity controller is activated in one of three modes:

| Mode | How | Use Case |
|------|-----|----------|
| Manual | `/singularity run` or `python lib/singularity.py run` | Ad-hoc single pass |
| Cron | `python lib/singularity.py run` in a crontab or scheduled task | Periodic checks (e.g., every 5 minutes) |
| Daemon | `/singularity daemon` or `python lib/singularity.py daemon` | Continuous background monitoring |

The controller is **inactive by default**. It must be explicitly started by the user.

## Safety Boundaries

### Never Auto-Execute

The Singularity MUST NEVER autonomously:

| Prohibited Action | Why |
|-------------------|-----|
| Act on circuit breaker OPEN events | Requires human judgment; underlying issue may be systemic |
| Exceed daily budget | Financial safety; respects `resources.budget.daily_alert_usd` from `cognitive-os.yaml` |
| Run more than 3 parallel pipelines | Resource protection; prevents context exhaustion |
| Reprocess the same event within 1 hour | Cooldown prevents thrashing on transient issues |
| Modify database schemas or migrations | Data safety; irreversible changes require human approval |
| Change authentication/authorization code | Security-critical; requires human review |
| Modify `.env` files or secrets | Credential safety |
| Push to remote without human approval | Git safety |

### Human Escalation Triggers

The controller MUST escalate to a human (via notification) when:

1. **Circuit breaker is OPEN** -- always, no exceptions
2. **Daily budget is exhausted** -- log and stop, notify user
3. **Pipeline fails twice for the same event type** -- potential systemic issue
4. **Event requires code changes in production/maintenance phase** -- conservative mode
5. **Unknown event type detected** -- defensive handling

### Budget Limits Per Cycle

| Constraint | Value | Source |
|------------|-------|--------|
| Daily budget | `resources.budget.daily_alert_usd` | `cognitive-os.yaml` |
| Per-pipeline max | `resources.budget.per_agent_max_usd` | `cognitive-os.yaml` |
| Cycle cost tracking | Logged to `metrics/cost-events.jsonl` | Automatic |

When budget reaches 80%, the controller downgrades models (opus -> sonnet -> haiku).
When budget reaches 100%, the controller STOPS all pipeline launches.

## Phase-Dependent Behavior

| Phase | Allowed Event Types | Auto-Execute |
|-------|--------------------|----|
| `reconstruction` | ALL event types | Full autonomy (within safety boundaries) |
| `stabilization` | ALL event types | Full autonomy (within safety boundaries) |
| `production` | `test_failure`, `stale_docs`, `kpi_degradation`, `coverage_drop` | Conservative -- no new features or code repairs without approval |
| `maintenance` | `test_failure`, `stale_docs`, `kpi_degradation`, `coverage_drop` | Conservative -- same as production |

In production/maintenance, events like `new_feature`, `bug_report`, `error_pattern`, and `skill_failure` are logged but NOT executed. They appear in the status report for human review.

## Event Priority Queue

Events are processed in this strict priority order:

1. `circuit_open` -- logged and escalated (never executed)
2. `test_failure` -- immediate repair
3. `bug_report` -- fix reported bugs
4. `error_pattern` -- prevent recurring issues
5. `kpi_degradation` -- maintain quality standards
6. `coverage_drop` -- maintain coverage
7. `new_feature` -- implement requested features
8. `skill_failure` -- improve tooling
9. `stale_docs` -- documentation freshness

## Event Deduplication

Each event gets a dedup key (MD5 hash of type + source + detail). Once processed, the key is recorded in `metrics/singularity-events.jsonl`. Future cycles skip events with known keys.

The dedup window is session-scoped: restarting the daemon reloads processed keys from the log.

## Cooldown Policy

After processing an event of a given type, no events of that same type are processed for 1 hour. This prevents:
- Thrashing on recurring test failures
- Repeatedly filing the same bug
- Processing the same stale docs entry multiple times

## Monitoring the Singularity (Meta-Monitoring)

The Singularity itself is monitored via:

| Metric | File | What It Tracks |
|--------|------|----------------|
| Cycle summaries | `metrics/singularity-events.jsonl` | Detected/planned/executed/succeeded/failed per cycle |
| Cost tracking | `metrics/cost-events.jsonl` | Per-pipeline cost with `agent: singularity:{pipeline}` |
| Success rates | In-memory + status command | Per-event-type success percentage |
| Notifications | Configured provider (Telegram/Slack/webhook) | Failures and escalations |

Run `/singularity status` to see current state, cooldowns, success rates, and daily spend.

## Integration with Other Rules

| Rule | Integration |
|------|-------------|
| `resource-governance` | Budget limits enforced before each pipeline launch |
| `auto-repair` | Test failure events route to the auto-repair system |
| `error-learning` | Error patterns detected from `error-learning.jsonl` |
| `self-improvement-protocol` | Error patterns route to `/self-improve` |
| `agent-kpis` | KPI degradation triggers `/metrics-calibrator` |
| `doc-sync` | Stale docs route to `/doc-sync` |
| `cost-tracking` | All pipeline costs logged and tracked |
| `fault-tolerance` | Graceful shutdown on SIGTERM; event dedup prevents re-work |

## Configuration

The Singularity reads configuration from `cognitive-os.yaml`:

```yaml
# Relevant sections:
resources:
  budget:
    daily_alert_usd: 10     # Daily budget cap
    per_agent_max_usd: 2.00 # Per-pipeline cap

project:
  phase: reconstruction     # Determines allowed event types
```

## Contextual Trigger

This rule is loaded when: singularity, autonomous, mape-k, daemon, codebase health.
