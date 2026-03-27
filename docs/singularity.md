# Codebase Singularity

## What Is the Codebase Singularity?

The Codebase Singularity is the central autonomous controller for Cognitive OS. It implements a continuous MAPE-K (Monitor-Analyze-Plan-Execute-Knowledge) loop that detects codebase health events, classifies them, selects the right pipeline, executes it, and feeds outcomes back into persistent knowledge.

It is the point where all autonomous capabilities converge: auto-repair, self-improvement, doc-sync, coverage enforcement, KPI calibration, and issue-to-PR pipelines are all orchestrated through a single control loop.

## How It Works — The MAPE-K Loop

```
   MONITOR          ANALYZE          PLAN            EXECUTE         KNOWLEDGE
 +-----------+   +-----------+   +-----------+   +-----------+   +-----------+
 | Poll for  |-->| Classify  |-->| Priority  |-->| Launch    |-->| Record    |
 | events:   |   | & filter: |   | queue,    |   | pipeline  |   | outcomes, |
 | - GitHub  |   | - dedup   |   | budget,   |   | via       |   | update    |
 | - metrics |   | - cooldown|   | concurr., |   | Claude    |   | metrics,  |
 | - errors  |   | - phase   |   | phase     |   | Executor  |   | notify    |
 | - KPIs    |   |   gate    |   | gate      |   |           |   |           |
 +-----------+   +-----------+   +-----------+   +-----------+   +-----------+
       ^                                                               |
       +---------------------------------------------------------------+
                            feedback loop
```

### 1. MONITOR Phase

The controller polls multiple sources for actionable events:

| Source | What It Detects | Check Method |
|--------|----------------|--------------|
| GitHub Issues | Issues labeled `[sdd-auto]` | `gh issue list --label sdd-auto` |
| Error Learning | 3+ same-type errors in 24h | Reads `metrics/error-learning.jsonl` |
| Stale Docs | Documentation out of sync with code | Reads `metrics/stale-docs.jsonl` |
| KPI History | Quality score drops > 10% | Compares last 2 entries in `metrics/kpi-history.jsonl` |
| Skill Metrics | 3+ consecutive skill failures | Reads `metrics/skill-metrics.jsonl` |
| Coverage | Coverage drops > 5 percentage points | Reads `metrics/coverage-history.jsonl` |
| Circuit Breakers | OPEN breaker states | Reads `metrics/circuit-breaker/*.json` |

### 2. ANALYZE Phase

Events are filtered through three gates:

- **Deduplication**: Events with previously processed dedup keys are skipped
- **Cooldown**: Same event type not reprocessed within 1 hour
- **Phase gating**: Production/maintenance restricts allowed event types

### 3. PLAN Phase

The planner applies constraints:

- **Priority queue**: Circuit breaker > test failures > bugs > error patterns > features > docs
- **Budget check**: Stops if daily spend exceeds `resources.budget.daily_alert_usd`
- **Concurrency limit**: Max 3 parallel pipeline executions
- **Phase restriction**: In production/maintenance, only safe event types proceed

### 4. EXECUTE Phase

Each planned event launches the appropriate pipeline via `ClaudeExecutor`:

| Event Type | Pipeline | What It Does |
|------------|----------|-------------|
| `new_feature` | issue-to-pr | Creates SDD pipeline from GitHub issue |
| `bug_report` | issue-to-pr (bug mode) | Investigates and fixes reported bug |
| `test_failure` | auto-repair | Applies known fixes for failing tests |
| `stale_docs` | doc-sync | Updates documentation to match code |
| `error_pattern` | self-improve | Analyzes recurring errors and proposes fixes |
| `kpi_degradation` | metrics-calibrator | Recalibrates KPI thresholds |
| `coverage_drop` | coverage-enforcement | Generates tests for uncovered code |
| `skill_failure` | skill-creator | Improves failing skills |
| `circuit_open` | NONE | Escalated to human -- never auto-acted |

### 5. KNOWLEDGE Phase

After each pipeline execution:

- Outcome logged to `metrics/singularity-events.jsonl`
- Cost logged to `metrics/cost-events.jsonl`
- Success rates tracked per event type
- Failures trigger notifications via configured provider
- Dedup key recorded to prevent reprocessing

## Event Types and Routing Table

| Priority | Event Type | Source | Pipeline | Model | Auto-Execute |
|----------|-----------|--------|----------|-------|--------------|
| 1 | `circuit_open` | circuit-breaker/ | HUMAN | - | NEVER |
| 2 | `test_failure` | error-learning.jsonl | auto-repair | sonnet | Yes |
| 3 | `bug_report` | GitHub issues | issue-to-pr | sonnet | Yes |
| 4 | `error_pattern` | error-learning.jsonl | self-improve | sonnet | reconstruction/stabilization only |
| 5 | `kpi_degradation` | kpi-history.jsonl | metrics-calibrator | sonnet | Yes |
| 6 | `coverage_drop` | coverage-history.jsonl | coverage-enforcement | sonnet | Yes |
| 7 | `new_feature` | GitHub issues | issue-to-pr | sonnet | reconstruction/stabilization only |
| 8 | `skill_failure` | skill-metrics.jsonl | skill-creator | sonnet | reconstruction/stabilization only |
| 9 | `stale_docs` | stale-docs.jsonl | doc-sync | haiku | Yes |

## Safety Boundaries

### Hard Limits (Never Violated)

1. **Circuit breaker OPEN events are ALWAYS escalated to human** -- the controller logs a warning, sends a notification, and moves on. It never attempts to auto-resolve a circuit breaker state.

2. **Daily budget is enforced** -- when spend reaches the configured daily limit, all pipeline launches stop. The controller continues monitoring but takes no action.

3. **Concurrency is capped at 3** -- prevents resource exhaustion from too many parallel Claude executions.

4. **Event cooldown of 1 hour per type** -- prevents thrashing on recurring issues.

### Phase-Dependent Safety

In production and maintenance phases, the controller operates conservatively:
- Only `test_failure`, `stale_docs`, `kpi_degradation`, and `coverage_drop` are auto-executed
- New features, bug reports, error patterns, and skill failures are logged but deferred for human review

## How to Enable/Disable

### Enable (One-Time Run)

```bash
python lib/singularity.py run
# or
python lib/singularity.py dry-run  # preview only
```

### Enable (Continuous Daemon)

```bash
python lib/singularity.py daemon --interval 300 --budget 10.0
```

### Enable (Cron Schedule)

```cron
*/5 * * * * cd /path/to/project && python lib/singularity.py run >> /var/log/singularity.log 2>&1
```

### Disable

- Stop the daemon process (SIGTERM or Ctrl+C)
- Remove the cron entry
- The controller is inactive by default -- it does nothing unless explicitly started

### Check Status

```bash
python lib/singularity.py status
```

## Monitoring the Singularity (Meta-Monitoring)

The Singularity controller is itself observable:

| What to Check | How | Healthy Signal |
|---------------|-----|----------------|
| Is it running? | `python lib/singularity.py status` | Shows recent cycles |
| Is it spending too much? | Check `daily_spend_usd` in status output | Below daily budget |
| Is it effective? | Check `success_rates` in status output | > 70% per event type |
| Is it stuck? | Check `active_cooldowns` in status | Cooldowns cycling normally |
| Full audit trail | `tail metrics/singularity-events.jsonl \| jq .` | Regular cycle entries |

### Warning Signs

- Success rate below 50% for any event type: pipeline or detection logic may need tuning
- Daily spend approaching budget with many events remaining: consider increasing budget or reducing polling interval
- Same event type consistently in cooldown: underlying issue not being resolved

## Architecture

```
lib/singularity.py
  |
  +-- monitor_all()          # Polls all event sources
  |     +-- _monitor_github_issues()
  |     +-- _monitor_error_patterns()
  |     +-- _monitor_stale_docs()
  |     +-- _monitor_kpi_degradation()
  |     +-- _monitor_skill_failures()
  |     +-- _monitor_circuit_breakers()
  |     +-- _monitor_coverage()
  |
  +-- analyze()              # Dedup, cooldown, filter
  +-- plan()                 # Priority, budget, concurrency
  +-- execute_event()        # Launch pipeline via ClaudeExecutor
  +-- record_knowledge()     # Log outcomes, notify failures
  |
  +-- SingularityController  # Ties it all together
        +-- run_once()       # Single MAPE-K cycle
        +-- run_daemon()     # Continuous loop with SIGTERM handling
        +-- status()         # Current state report
```

## Dependencies

- Python 3.9+
- `claude` CLI installed and on PATH (for pipeline execution)
- `gh` CLI (for GitHub issue monitoring -- optional, gracefully degrades)
- `lib/claude_executor.py` -- subprocess executor with cost tracking
- `lib/notifications.py` -- multi-provider notification system
