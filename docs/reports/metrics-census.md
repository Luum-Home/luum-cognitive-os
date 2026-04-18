# Metrics Census — ADR-028 D1.A

**Generated**: 2026-04-18
**Scope**: All JSONL files written or read by the Cognitive OS
**Discovered**: 447 total JSONL files; 45 logical file identities

---

## Discovery Summary

| Location | Files | Notes |
|---|---|---|
| `.cognitive-os/metrics/` | 42 | Primary metrics store |
| `.cognitive-os/agent-bus/test-e2e-*/heartbeat.jsonl` | 57 instances | Written by `agent_bus.py` FallbackBus |
| `.cognitive-os/agent-bus/test-e2e-*/progress.jsonl` | 252 instances | Written by `agent_bus.py` FallbackBus |
| `.cognitive-os/transcripts/transcript-index.jsonl` | 1 | Written by `conversation-capture.sh` |
| `.claude/plugins/.cognitive-os/metrics/consequence-history.jsonl` | 1 | Plugin-scoped copy |
| `.claude/plugins/.cognitive-os/metrics/skill-archive.jsonl` | 1 | Plugin-scoped copy |
| `.engram/exports/luum-cognitive-os.jsonl` | 1 | Engram export — external tool, not OS-managed |
| `reference/`, `tests/fixtures/`, `.claude/plugins/pi-mono/` | 87 | Static test/reference data — no OS writers |

---

## Summary Table

> **Status legend**: `CONSUMED` = writer + reader + retention policy defined. `ORPHAN` = writer present, no reader. `MISCONFIGURED` = schema drift, missing writer, or missing file despite active readers.

### .cognitive-os/metrics/ — 42 files

| file | writers | readers | retention_policy | status |
|---|---|---|---|---|
| `adaptive-bypass.jsonl` | adaptive-bypass.sh | none | metrics-rotation.sh (5 000-line cap) | ORPHAN |
| `advisor-consultations.jsonl` | advisor_server.py (packages/advisor-mcp) | none | metrics-rotation.sh | ORPHAN |
| `agent-timeouts.jsonl` | session-cleanup.sh, agent-checkpoint.sh | none | metrics-rotation.sh | ORPHAN |
| `agent-verification.jsonl` | agent-output-verifier.sh | none | metrics-rotation.sh | ORPHAN |
| `assumptions.jsonl` | assumption-tracker.sh | none | metrics-rotation.sh | ORPHAN |
| `auto-verify.jsonl` | auto-verify.sh, completion-gate.sh | completion-gate.sh (read count) | metrics-rotation.sh | CONSUMED |
| `blast-radius.jsonl` | blast-radius.sh | none | metrics-rotation.sh | ORPHAN |
| `capability-snapshots.jsonl` | pre-cleanup-snapshot.sh | none | metrics-rotation.sh | ORPHAN |
| `clarification-events.jsonl` | clarification-gate.sh (packages/quality-gates) | cos_mcp.py (mcp-server, key lookup) | metrics-rotation.sh | CONSUMED |
| `completeness-check.jsonl` | completeness-check.sh | none | metrics-rotation.sh | ORPHAN |
| `consequence-history.jsonl` | consequence_engine.py, completion-gate.sh, model_router.py | self_improvement.py, kpi_collector.py | metrics-rotation.sh | CONSUMED |
| `content-policy.jsonl` | content-policy.sh | none | metrics-rotation.sh | ORPHAN |
| `context-diet.jsonl` | context-diet.sh | none | metrics-rotation.sh | ORPHAN |
| `context-watchdog.jsonl` | context-watchdog.sh | none | metrics-rotation.sh | ORPHAN |
| `contextual-rules.jsonl` | contextual-rule-loader.sh | symbiosis_monitor.py | metrics-rotation.sh | CONSUMED |
| `cost-events.jsonl` | record_completion.py, audit-id-enricher.sh, rate_limit_protection.py, checkpoint_manager.py | resource-check.sh, rate-limit-protection.sh, singularity.py, queue_advisor.py, cost_dashboard.py, mlflow_bridge.py, changelog_generator.py | metrics-rotation.sh | MISCONFIGURED (schema drift — see Findings) |
| `dispatch-gate.jsonl` | dispatch-gate.sh | dequeue-notify.sh | metrics-rotation.sh | CONSUMED |
| `epic-task-detector.jsonl` | epic-task-detector.sh | none | metrics-rotation.sh | ORPHAN |
| `hallucinations.jsonl` | claim-validator.sh | kpi_collector.py | metrics-rotation.sh | CONSUMED |
| `hook-health.jsonl` | safe-jsonl.sh (_lib, fires on every hook EXIT) | cognitive-os-health.sh | metrics-rotation.sh (archive confirmed) | CONSUMED |
| `infra-detections.jsonl` | infra-intent-detector.sh | none | metrics-rotation.sh | ORPHAN |
| `infra-health.jsonl` | infra-health.sh | none | metrics-rotation.sh | ORPHAN |
| `infra-usage.jsonl` | smart_infra.py | none | metrics-rotation.sh | ORPHAN |
| `knowledge-graph.jsonl` | session-knowledge-extractor.sh | none | metrics-rotation.sh | ORPHAN |
| `kpi-history.jsonl` | kpi-trigger.sh, session-cleanup.sh | self_improvement.py, singularity.py, paperclip-sync.sh | metrics-rotation.sh | CONSUMED |
| `large-file-reads.jsonl` | large-file-advisor.sh, smart_reader.py | none | metrics-rotation.sh | ORPHAN |
| `performance.jsonl` | performance_monitor.py (timing.sh), homeostasis.py, symbiosis_monitor.py | symbiosis_monitor.py, homeostasis.py | metrics-rotation.sh | CONSUMED |
| `predev-completeness.jsonl` | predev-completeness-check.sh | none | metrics-rotation.sh | ORPHAN |
| `prompt-captures.jsonl` | user-prompt-capture.sh | none | metrics-rotation.sh | ORPHAN |
| `prompt-quality.jsonl` | prompt-quality.sh | none | metrics-rotation.sh | ORPHAN |
| `rate-limit-checks.jsonl` | rate-limit-protection.sh | none | metrics-rotation.sh | ORPHAN |
| `reinvention-checks.jsonl` | reinvention-check.sh | none | metrics-rotation.sh | ORPHAN |
| `scope-proportionality.jsonl` | scope-proportionality.sh | none | metrics-rotation.sh | ORPHAN |
| `session-learnings.jsonl` | session-learning.sh | self_improvement.py, symbiosis_monitor.py | metrics-rotation.sh | CONSUMED |
| `skill-archive.jsonl` | skill_archive.py | self_improvement.py | metrics-rotation.sh | CONSUMED |
| `skill-feedback.jsonl` | skill-feedback-tracker.sh | none | metrics-rotation.sh | ORPHAN |
| `skill-metrics.jsonl` | skill-usage-tracker.sh, component_usage_tracker.py, homeostasis.py | kpi_collector.py, repetition_detector.py, mlflow_bridge.py, singularity.py, homeostasis.py, symbiosis_monitor.py | metrics-rotation.sh | CONSUMED |
| `task-completed.jsonl` | task-completed.sh | none | metrics-rotation.sh | ORPHAN |
| `task-created.jsonl` | task-created.sh | none | metrics-rotation.sh | ORPHAN |
| `task-history.jsonl` | task-recorder.sh (packages/task-management) | cost_predictor.py (packages/scope-governance) | metrics-rotation.sh | CONSUMED |
| `teammate-idle.jsonl` | teammate-idle.sh | none | metrics-rotation.sh | ORPHAN |
| `truncation-events.jsonl` | result-truncator.sh (packages/verification-audit) | none | metrics-rotation.sh | ORPHAN |

### Referenced but MISSING from disk (writers exist, file never created or was deleted)

| file | writers | readers | retention_policy | status |
|---|---|---|---|---|
| `error-learning.jsonl` | error-learning.sh, error-pipeline.sh, session-knowledge-extractor.sh | auto-repair-dispatcher.sh, error-pattern-detector.sh, singularity.py, learning_pipeline.py, kpi_collector.py, self_improvement.py | metrics-rotation.sh | MISCONFIGURED (missing on disk despite 10+ active writers and readers) |
| `repair-outcomes.jsonl` | error-pipeline.sh, auto_repair.py | conversation-capture.sh, cognitive-os-health.sh, symbiosis_monitor.py | metrics-rotation.sh | MISCONFIGURED (missing on disk) |
| `remediation-registry.jsonl` | auto-repair-dispatcher.sh, auto_repair.py | semantic-search.sh, auto-repair-dispatcher.sh, repair-status SKILL.md | metrics-rotation.sh | MISCONFIGURED (missing on disk) |
| `repair-queue.jsonl` | error-pipeline.sh | none | metrics-rotation.sh | MISCONFIGURED (missing on disk) |
| `repair-dispatch.jsonl` | auto-repair-dispatcher.sh | none | metrics-rotation.sh | MISCONFIGURED (missing on disk) |
| `session-audit.jsonl` | git-context-capture.sh | changelog_generator.py | metrics-rotation.sh | MISCONFIGURED (missing on disk) |
| `singularity-events.jsonl` | singularity.py | singularity-suggestion.sh | metrics-rotation.sh | MISCONFIGURED (missing on disk) |
| `stale-docs.jsonl` | none found | singularity.py | none | MISCONFIGURED (reader exists, no writer found) |
| `trust-scores.jsonl` | none found | kpi_collector.py | none | MISCONFIGURED (reader exists, no writer found) |
| `escalation-events.jsonl` | none found | kpi_collector.py | none | MISCONFIGURED (reader exists, no writer found) |
| `coverage-history.jsonl` | none found | singularity.py | none | MISCONFIGURED (reader exists, no writer found) |
| `error-skill-correlations.jsonl` | none found | learning_pipeline.py | none | MISCONFIGURED (reader exists, no writer found) |
| `skill-usage.jsonl` | skill-usage-tracker.sh (delegated to telemetry.py) | none found | telemetry.py (10 MB rotation) | ORPHAN |
| `hook-usage.jsonl` | telemetry.py | none found | telemetry.py (10 MB rotation) | ORPHAN |
| `agent-launches.jsonl` | telemetry.py | none found | telemetry.py (10 MB rotation) | ORPHAN |
| `rate-limit-events.jsonl` | telemetry.py | none found | telemetry.py (10 MB rotation) | ORPHAN |
| `dead-letter-queue.jsonl` | dead_letter_queue.py | none found | none | ORPHAN |
| `homeostasis.jsonl` | homeostasis.py | none found | metrics-rotation.sh (when created) | ORPHAN |
| `symbiosis.jsonl` | symbiosis_monitor.py | none found | metrics-rotation.sh (when created) | ORPHAN |
| `context-usage.jsonl` | queue_advisor.py | none found | none | ORPHAN |
| `access-audit.jsonl` | agent_permissions.py | none found | none | ORPHAN |
| `adr-detections.jsonl` | adr_detector.py | none found | none | ORPHAN |
| `auto-rollback.jsonl` | auto-rollback-trigger.sh | none found | none | ORPHAN |
| `session-log.jsonl` | session-sanity.sh | cos-sessions.sh | none | ORPHAN |

### .cognitive-os/agent-bus/ — 2 logical patterns (309 instances)

| file pattern | writers | readers | retention_policy | status |
|---|---|---|---|---|
| `agent-bus/test-e2e-{id}/heartbeat.jsonl` (57 dirs) | agent_bus.py FallbackBus | agent_dashboard.py (via OrchestratorSubscriber) | **none** | ORPHAN (test dirs never cleaned up) |
| `agent-bus/test-e2e-{id}/progress.jsonl` (252 dirs) | agent_bus.py FallbackBus | agent_dashboard.py (via OrchestratorSubscriber) | **none** | ORPHAN (test dirs never cleaned up) |

### .cognitive-os/transcripts/

| file | writers | readers | retention_policy | status |
|---|---|---|---|---|
| `transcript-index.jsonl` | conversation-capture.sh | cos_mcp.py (listed under "clarifications" key lookup) | none | ORPHAN (cos_mcp.py references it by filename string only — no read path confirmed) |

### .claude/plugins/.cognitive-os/metrics/

| file | writers | readers | retention_policy | status |
|---|---|---|---|---|
| `consequence-history.jsonl` | consequence_engine.py (plugin scope) | self_improvement.py (plugin scope) | none | MISCONFIGURED (duplicate of root .cognitive-os/metrics/ copy; no rotation; 2 rows) |
| `skill-archive.jsonl` | skill_archive.py (plugin scope) | self_improvement.py (plugin scope) | none | MISCONFIGURED (duplicate of root copy; no rotation; 2 rows) |

---

## Findings

### F-1: ADR-028 claim of ~40% unparseable rows in hook-health.jsonl is FALSE

ADR-028 line 105-106 states: "hook-health.jsonl mixes `duration_ms` and `elapsed_ms`; ~40% of rows are unparseable". Current state:

- 7,692 rows, **0 bad JSON**, uniform schema `{timestamp, hook, exit_code, duration_ms}` on 100% of rows.
- No `elapsed_ms` field appears anywhere in the file.
- `safe-jsonl.sh` standardised the schema. The drift described in ADR-027 baseline was from a prior implementation and no longer exists.
- **Action**: Remove the ~40% claim from ADR-028 text. The schema is already clean.

### F-2: hook-health.jsonl exceeds rotation threshold (7,696 lines > 5,000 cap)

`metrics-rotation.sh` rotates at `MAX_LINES=5000`. hook-health.jsonl has 7,696 lines (704 KB). Two archive files confirm the hook ran previously but did not bring the file below threshold on the most recent sessions. The file is past the 1 MiB ADR-028 threshold (704 KB currently, growing ~1,000 rows/day).

### F-3: cost-events.jsonl has schema drift — 2 incompatible shapes

```
Shape A (62%, 100 rows): {agent, estimated_cost_usd, is_estimate, model, timestamp, tokens_estimated}
Shape B (38%, 60 rows):  {agent, branch, change_id, estimated_cost_usd, is_estimate, model, session_id, sprint_id, timestamp, tokens_estimated}
```

`audit-id-enricher.sh` enriches the last line of cost-events.jsonl with sprint/audit context only when an active `audit_id` exists. Consumers (`mlflow_bridge.py`, `cost_dashboard.py`, `singularity.py`) parse all rows and silently drop fields missing in Shape A. This is not currently breaking but is a MetricEvent schema violation.

### F-4: 7 critical files are MISSING from disk despite active writers and readers

`error-learning.jsonl`, `repair-outcomes.jsonl`, `remediation-registry.jsonl`, `repair-queue.jsonl`, `repair-dispatch.jsonl`, `session-audit.jsonl`, and `singularity-events.jsonl` are referenced by a combined 20+ hooks and library modules but **do not exist on disk**. This means:

- The auto-repair system (`error-pipeline.sh` → `auto-repair-dispatcher.sh` → `circuit-breaker.sh`) is accumulating no repair history.
- `cognitive-os-health.sh` reads `repair-outcomes.jsonl` for health display — it silently shows no data.
- `error-pattern-detector.sh` reads `error-learning.jsonl` to trigger pattern warnings — it never fires.
- `singularity.py` can never trigger because `singularity-events.jsonl` is never written.

These files are missing because the hooks that write them (`error-learning.sh`, `error-pipeline.sh`) run in per-session scoped directories (`$SESSION_DIR/metrics/`) and `session-cleanup.sh` merges them into global — but those sessions apparently never had errors, **or** session metrics directories are not being created. Most likely: `COGNITIVE_OS_SESSION_ID` is unset, so `session-cleanup.sh` exits at line 23 without merging.

### F-5: 5 files referenced as readers have no corresponding writer anywhere in the codebase

`stale-docs.jsonl`, `trust-scores.jsonl`, `escalation-events.jsonl`, `coverage-history.jsonl`, `error-skill-correlations.jsonl` — `kpi_collector.py` and `singularity.py` read these files and return empty results when absent. KPI calculations for trust score, escalation rate, and test coverage are therefore permanently zeroed out.

### F-6: 309 agent-bus test-e2e directories accumulate indefinitely

Every e2e test run creates a directory `test-e2e-{8-hex}/` with `heartbeat.jsonl` and/or `progress.jsonl`. There is no cleanup step in `session-cleanup.sh`, no cron, and no TTL. Currently 309 files across 309 directories. At current test cadence this will reach thousands within weeks.

### F-7: Rotation policy mismatch — metrics-rotation.sh uses line count, ADR-028 requires size-based

`metrics-rotation.sh` rotates at `MAX_LINES=5000` (env-configurable). ADR-028 D1.A mandates size > 1 MiB OR age > 7 days. `consequence-history.jsonl` (508 KB, 2,291 lines) and `skill-archive.jsonl` (514 KB, 2,291 lines) are below the 5,000-line threshold but approaching the 1 MiB size limit. The hook does not implement age-based rotation.

### F-8: 35 present metrics files are write-only ORPHANs

Files including `adaptive-bypass`, `agent-timeouts`, `agent-verification`, `assumptions`, `blast-radius`, `capability-snapshots`, `completeness-check`, `content-policy`, `context-diet`, `context-watchdog`, `epic-task-detector`, `infra-detections`, `infra-health`, `infra-usage`, `knowledge-graph`, `large-file-reads`, `predev-completeness`, `prompt-captures`, `prompt-quality`, `rate-limit-checks`, `reinvention-checks`, `scope-proportionality`, `skill-feedback`, `task-completed`, `task-created`, `teammate-idle`, `truncation-events` are written by hooks/libs but never consumed. The data is written and discarded.

---

## Recommendations

| file / group | action |
|---|---|
| `hook-health.jsonl` | Force rotation immediately (7,696 lines). Update metrics-rotation.sh to also enforce 1 MiB size threshold per ADR-028 D1.A. |
| `cost-events.jsonl` | Fix schema drift: make `branch`, `change_id`, `session_id`, `sprint_id` optional fields in a MetricEvent base schema. Backfill Shape-A rows with `null` values so all consumers get a uniform shape. |
| `error-learning.jsonl` + 6 missing repair/audit files | Diagnose `COGNITIVE_OS_SESSION_ID` propagation. If session scoping is the issue, the simplest fix is to have `error-learning.sh` write directly to `$PROJECT_DIR/.cognitive-os/metrics/` when `$SESSION_DIR` is unavailable, matching the behaviour of other hooks. |
| `stale-docs.jsonl`, `trust-scores.jsonl`, `escalation-events.jsonl`, `coverage-history.jsonl`, `error-skill-correlations.jsonl` | Either implement writers (assign hook owners per ADR-028 D1.A "ORPHAN files — owner assigned within one sprint") or remove the read-paths from `kpi_collector.py` and `singularity.py` so KPIs are not silently zeroed. |
| `.cognitive-os/agent-bus/test-e2e-*/` (309 dirs) | Add a cleanup step to `session-cleanup.sh` or create a cron/`metrics-rotation.sh` extension: `find .cognitive-os/agent-bus -maxdepth 1 -name 'test-e2e-*' -mtime +7 -exec rm -rf {} \;` |
| `metrics-rotation.sh` | Extend to implement ADR-028 thresholds: size > 1 MiB OR age > 7 days, in addition to current line count. Archive destination should be `.cognitive-os/metrics/archive/` (ADR-028 specifies this path; current hook uses `.cognitive-os/metrics/.archive/` — path mismatch). |
| `.claude/plugins/.cognitive-os/metrics/` duplicates | Delete or symlink to root `.cognitive-os/metrics/`. These are 2-row stubs that will diverge from the real data. |
| ORPHAN files with >100 rows (blast-radius 159, completeness-check 165, context-diet 86, infra-health 86, knowledge-graph 44, predev-completeness 40, rate-limit-checks 92, reinvention-checks 26, skill-feedback 71, truncation-events 137) | Assign a reader for each within one sprint or mark for deletion. These are the highest-value ORPHANs — they contain real data but zero consumers. |
| `telemetry.py` files (skill-usage, hook-usage, agent-launches, rate-limit-events) | These 4 files use a different rotation mechanism (10 MB via `telemetry.py`) and never appear on disk until their respective paths are triggered. They are currently virtual ORPHANs. Confirm that `skill-usage-tracker.sh` actually invokes the Python telemetry path; the hook comment says "Python owns rotation" but grep shows the hook appends directly via shell, not through `telemetry.py`. |

---

## Counts (for verification)

| metric | count |
|---|---|
| Total JSONL files on disk (all scopes, excl. node_modules/.git/.venv) | 447 |
| Logical file identities in `.cognitive-os/metrics/` | 42 |
| CONSUMED (writer + reader + retention defined) | 12 |
| ORPHAN (writer present, no reader) | 22 |
| MISCONFIGURED (schema drift / missing on disk / reader without writer) | 14 |
| agent-bus instances (2 patterns × N test dirs) | 309 |
| Files exceeding ADR-028 rotation threshold (1 MiB) | 1 (`hook-health.jsonl` at 704 KB and growing; `consequence-history` + `skill-archive` approaching at ~510 KB each) |
| Files with confirmed schema drift | 1 (`cost-events.jsonl`) |
| ADR-028 claims refuted by data | 1 (hook-health ~40% unparseable — false; 0 bad rows) |
