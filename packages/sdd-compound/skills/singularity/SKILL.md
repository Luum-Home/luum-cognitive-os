<!-- SCOPE: both -->
---
name: singularity
version: 1.0.0
description: Codebase Singularity — autonomous MAPE-K control loop that monitors, classifies, and routes codebase events to the right pipeline
triggers:
  - /singularity
  - autonomous loop
  - mape-k
  - codebase health daemon
tags: [automation, mape-k, monitoring, self-healing, autonomous]
auto-generated: false
audience: project
summary_line: Codebase Singularity — autonomous MAPE-K control loop that monitors…

---

# Singularity — Autonomous MAPE-K Control Loop

The Codebase Singularity is the central autonomous controller that ties all Cognitive OS capabilities together. It continuously monitors the codebase for actionable events, classifies them, plans execution strategy, launches the right pipeline, and feeds outcomes back into persistent knowledge.

## Invoke

```
/singularity [status|run|daemon|dry-run]
```

## Subcommands

| Command | Description |
|---------|-------------|
| `status` | Show current state: processed events, active cooldowns, success rates, daily spend |
| `run` | Execute a single pass through the MAPE-K loop |
| `daemon` | Start continuous polling (default interval: 300s) |
| `dry-run` | Preview what would be detected and executed without running pipelines |

## CLI Usage

```bash
# Single pass (suitable for cron)
python lib/singularity.py run

# Preview without executing
python lib/singularity.py dry-run

# Continuous daemon with custom interval and budget
python lib/singularity.py daemon --interval 300 --budget 10.0

# Show current status
python lib/singularity.py status

# Verbose output
python lib/singularity.py run --verbose
```

## Event Types and Routing

| Event Type | Source | Routed To | Model |
|------------|--------|-----------|-------|
| `circuit_open` | `metrics/circuit-breaker/` | HUMAN ESCALATION (never auto-acted) | - |
| `test_failure` | `metrics/error-learning.jsonl` | auto-repair | sonnet |
| `bug_report` | GitHub issues (`sdd-auto` + `bug` label) | issue-to-pr (bug mode) | sonnet |
| `error_pattern` | `metrics/error-learning.jsonl` (3+ same-type/24h) | self-improve | sonnet |
| `kpi_degradation` | `metrics/kpi-history.jsonl` (10%+ drop) | metrics-calibrator | sonnet |
| `coverage_drop` | `metrics/coverage-history.jsonl` (5+ ppt drop) | coverage-enforcement | sonnet |
| `new_feature` | GitHub issues (`sdd-auto` label) | issue-to-pr | sonnet |
| `skill_failure` | `metrics/skill-metrics.jsonl` (3+ consecutive) | skill-creator | sonnet |
| `stale_docs` | `metrics/stale-docs.jsonl` | doc-sync | haiku |

## Safety Boundaries

1. **Circuit breaker events ALWAYS escalate to human** -- never auto-acted on
2. **Daily budget enforced** -- stops executing when spend exceeds `daily_alert_usd`
3. **Concurrency limited** -- max 3 parallel pipelines
4. **Cooldown per event type** -- 1 hour between processing same event type
5. **Event deduplication** -- same event not reprocessed
6. **Phase-dependent gating** -- production/maintenance restricts allowed event types

## Metrics

All activity is logged to `metrics/singularity-events.jsonl` with:
- Cycle summaries (detected, planned, executed, succeeded, failed)
- Per-event execution details (pipeline, cost, duration, success)
- Escalation records (circuit breaker events)
- Budget blocks and phase blocks

## Dependencies

- Python 3.9+
- `claude` CLI installed and on PATH
- `gh` CLI for GitHub issue monitoring
- `lib/claude_executor.py` for pipeline execution
- `lib/notifications.py` for alerts
