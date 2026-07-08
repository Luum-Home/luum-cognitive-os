---
type: concept-synthesis
source: docs/04-Concepts/root/singularity.md
provenance: "Autonomous capabilities (auto-repair, self-improvement, doc-sync, coverage enforcement, KPI calibration, issue-to-PR) were previously isolated and needed a single control loop to converge them."
---

## What it is
`lib/singularity.py` — the central autonomous controller implementing a continuous MAPE-K (Monitor-Analyze-Plan-Execute-Knowledge) loop that detects codebase health events, classifies them, selects a pipeline, executes it via `ClaudeExecutor`, and records outcomes.

## Key mechanics
- MONITOR: polls GitHub issues (`[sdd-auto]` label), `metrics/error-learning.jsonl` (3+ same-type in 24h), `metrics/stale-docs.jsonl`, `metrics/kpi-history.jsonl` (>10% drop), `metrics/skill-metrics.jsonl` (3+ consecutive failures), `metrics/coverage-history.jsonl` (>5pp drop), `metrics/circuit-breaker/*.json` (OPEN states).
- ANALYZE: dedup by key, 1-hour cooldown per event type, phase gating (production/maintenance restricts event types).
- PLAN: priority queue (circuit breaker > test failures > bugs > error patterns > features > docs), budget check against `resources.budget.daily_alert_usd`, concurrency capped at 3 parallel executions.
- EXECUTE routing table: `new_feature`/`bug_report` -> issue-to-pr, `test_failure` -> auto-repair, `stale_docs` -> doc-sync (haiku), `error_pattern` -> self-improve, `kpi_degradation` -> metrics-calibrator, `coverage_drop` -> coverage-enforcement, `skill_failure` -> skill-creator, `circuit_open` -> NEVER auto-acted (escalated to human). Most event types use `sonnet`; some are restricted to reconstruction/stabilization phase only.
- KNOWLEDGE: logs outcome to `metrics/singularity-events.jsonl`, cost to `metrics/cost-events.jsonl`, tracks per-event success rates, notifies on failure, records dedup key.
- Hard limits: circuit_open always escalated; daily budget enforced (launches stop at limit); concurrency capped at 3; 1-hour cooldown per event type.
- Enable via `SINGULARITY_ENABLED=true python3 lib/singularity.py {run|dry-run|daemon --interval 300 --budget 10.0|status}`; disabled by default.
- 5 scheduling options ranked by persistence: `CronCreate` (session-only, no portable equivalent outside Claude Code), Claude Code Scheduled Task (MCP), system crontab (recommended for production), daemon/`nohup` mode, launchd (macOS) / systemd (Linux) (most robust).
- Auto-suggestion (not auto-enable): `hooks/session-init.sh` checks 3 signals at SessionStart (never ran, 3+ errors/24h, stale docs pending) and prints a `=== SINGULARITY SUGGESTION ===` block on stderr; never auto-enables per `rules/resource-governance.md` budget rules.

## Relations & where used
Ties together auto-repair, self-improvement, doc-sync, coverage-enforcement, metrics-calibrator, skill-creator, and issue-to-pr pipelines. Cross-referenced with `docs/04-Concepts/architecture/cross-runtime-portability.md#scheduling--recurring-tasks`. Dependencies: Python 3.9+, `claude` CLI, `gh` CLI (optional, degrades gracefully), `lib/claude_executor.py`, `lib/notifications.py`.

## Status / caveats
Inactive by default — does nothing unless explicitly started (no daemon, no cron entry). Warning signs to monitor: success rate <50% for any event type, daily spend approaching budget with events remaining, same event type stuck in cooldown repeatedly.
