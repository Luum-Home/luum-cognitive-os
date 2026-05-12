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
SINGULARITY_ENABLED=true python3 lib/singularity.py run
# or
SINGULARITY_ENABLED=true python3 lib/singularity.py dry-run  # preview only
```

### Enable (Continuous Daemon)

```bash
SINGULARITY_ENABLED=true python3 lib/singularity.py daemon --interval 300 --budget 10.0
```

### Enable (Cron Schedule)

```cron
*/5 * * * * cd /path/to/project && PYTHONPATH=. SINGULARITY_ENABLED=true python3 lib/singularity.py run >> /var/log/singularity.log 2>&1
```

### Disable

- Stop the daemon process (SIGTERM or Ctrl+C)
- Remove the cron entry
- The controller is inactive by default -- it does nothing unless explicitly started

### Check Status

```bash
SINGULARITY_ENABLED=true python3 lib/singularity.py status
```

## Monitoring the Singularity (Meta-Monitoring)

The Singularity controller is itself observable:

| What to Check | How | Healthy Signal |
|---------------|-----|----------------|
| Is it running? | `SINGULARITY_ENABLED=true python3 lib/singularity.py status` | Shows recent cycles |
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

## Auto-Suggestion Protocol

Singularity is inactive by default. Rather than requiring users to remember to enable it, Cognitive OS proactively suggests activation when observable signals warrant it. Suggestions are advisory — they never block session startup or normal work.

### Primary Implementation: SessionStart

`hooks/session-init.sh` runs at the start of every Claude Code session. It checks three signals using only file existence tests and line counts (no heavy parsing, < 200ms total):

| Signal | Check | Suggestion Shown |
|--------|-------|-----------------|
| Never ran | `singularity-events.jsonl` does not exist | Suggest dry-run as a first-time introduction |
| Active errors | `error-learning.jsonl` has 3+ entries in last 24h | Suggest activation for autonomous error monitoring |
| Stale docs pending | `stale-docs.jsonl` exists and is non-empty | Mention doc-sync pipeline as a quick win |

The output appears as a clearly delimited block on stderr so it is visible but does not clutter normal output:

```
=== SINGULARITY SUGGESTION ===
Detected: 5 errors in last 24h, 2 stale docs
Consider activating Singularity for autonomous monitoring.
Try: SINGULARITY_ENABLED=true python3 lib/singularity.py dry-run
=== END SINGULARITY ===
```

If Singularity has never run:

```
=== SINGULARITY SUGGESTION ===
Singularity has never been run in this project.
Try: SINGULARITY_ENABLED=true python3 lib/singularity.py dry-run
=== END SINGULARITY ===
```

SessionStart is the primary implementation point because it is zero-cost (no API calls, no subprocess), runs every session unconditionally, and catches the "never tried it" case that hook-based triggers would miss.

### Secondary Triggers (Contextual)

These points already have hooks or reporting infrastructure. Adding a suggestion line is low-effort and contextually relevant:

| Trigger Point | Signal | Suggestion |
|---------------|--------|------------|
| After sdd-verify FAIL x3 | Auto-rollback triggered | Suggest Singularity for early pattern detection before the next feature cycle |
| After `/cognitive-os-init` | Fresh project setup | Include in onboarding checklist as an optional next step |
| KPI degradation | `kpi-trigger.sh` detects score drop | Suggest continuous monitoring to catch future regressions automatically |

These are lower-priority than the SessionStart check and should be implemented as one-line additions to the existing hook output rather than new hook files.

### Why Not Auto-Enable

Singularity launches Claude pipelines autonomously, which costs tokens and money. Auto-enabling without user consent would violate the budget governance rules in `rules/resource-governance.md`. The suggestion pattern — show signal, recommend dry-run, let user decide — respects user agency while still surfacing the option at the right moment.

## Scheduling Options

The Singularity can be triggered in five ways. Choose based on persistence and vendor requirements.

> For the full portability comparison across IDEs, see [`docs/04-Concepts/architecture/cross-runtime-portability.md#scheduling--recurring-tasks`](architecture/cross-runtime-portability.md#scheduling--recurring-tasks).

| Option | Persists across sessions | Survives reboots | Independent of Claude Code | Best for |
|--------|--------------------------|-----------------|---------------------------|----------|
| `CronCreate` (in-session) | No | No | No | Quick experiments only |
| Claude Code Scheduled Task (MCP) | Yes | No | No (needs Claude Code) | Claude Code-only setups |
| System crontab | Yes | Yes | Yes | Production (recommended) |
| Daemon mode (`nohup`) | Until reboot | No | Yes | Development / staging |
| launchd / systemd | Yes | Yes | Yes | Production (most robust) |

### Option 1: Session-only (CronCreate)

Runs inside the current Claude Code session. Dies when the session ends. Use only for testing.

```
# Within a Claude Code session:
# CronCreate with interval: 300 seconds
# Prompt: "cd /path/to/project && PYTHONPATH=. SINGULARITY_ENABLED=true python3 lib/singularity.py run"
```

**Warning**: `CronCreate` has no portable equivalent in Cursor, Windsurf, or Kiro. Do not rely on it for production scheduling.

### Option 2: Claude Code Durable Scheduled Task

Survives individual sessions but still requires the Claude Code runtime.

```bash
# Via MCP tool: mcp__scheduled-tasks__create_scheduled_task
# schedule: "*/5 * * * *"
# prompt: "cd /path/to/project && PYTHONPATH=. SINGULARITY_ENABLED=true python3 lib/singularity.py run"
```

### Option 3: System Crontab (recommended for production)

Vendor-independent. Runs as an OS process, unaffected by which IDE is in use.

```bash
crontab -e
# Add:
*/5 * * * * cd /path/to/project && PYTHONPATH=. SINGULARITY_ENABLED=true python3 lib/singularity.py run >> /var/log/singularity.log 2>&1
```

### Option 4: Daemon Mode

Long-running background process. Survives session ends but not reboots.

```bash
PYTHONPATH=. SINGULARITY_ENABLED=true nohup python3 lib/singularity.py daemon --interval 300 --budget 10.0 >> /var/log/singularity.log 2>&1 &
echo $! > /var/run/singularity.pid  # save PID for later kill
```

### Option 5: launchd (macOS) / systemd (Linux)

Most robust option — survives reboots, managed by the OS supervisor.

**macOS launchd** (`~/Library/LaunchAgents/com.luum.singularity.plist`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.luum.singularity</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/path/to/project/lib/singularity.py</string>
    <string>run</string>
  </array>
  <key>WorkingDirectory</key><string>/path/to/project</string>
  <key>StartInterval</key><integer>300</integer>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONPATH</key><string>/path/to/project</string>
    <key>SINGULARITY_ENABLED</key><string>true</string>
  </dict>
  <key>StandardOutPath</key><string>/var/log/singularity.log</string>
  <key>StandardErrorPath</key><string>/var/log/singularity.log</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.luum.singularity.plist
```

**Linux systemd** — create two unit files, then enable the timer:

`~/.config/systemd/user/singularity.service`:

```ini
[Unit]
Description=Cognitive OS Singularity controller (single run)
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 /path/to/project/lib/singularity.py run
Environment="PYTHONPATH=/path/to/project"
Environment="SINGULARITY_ENABLED=true"
StandardOutput=append:/var/log/singularity.log
StandardError=append:/var/log/singularity.log
```

`~/.config/systemd/user/singularity.timer`:

```ini
[Unit]
Description=Run Singularity controller every 5 minutes

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now singularity.timer
systemctl --user status singularity.timer
```

## Dependencies

- Python 3.9+
- `claude` CLI installed and on PATH (for pipeline execution)
- `gh` CLI (for GitHub issue monitoring -- optional, gracefully degrades)
- `lib/claude_executor.py` -- subprocess executor with cost tracking
- `lib/notifications.py` -- multi-provider notification system
