<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Performance Monitoring Protocol

## Purpose

Track latency, throughput, overhead, and health of every Cognitive OS component. This is the "Micrometer/Actuator" equivalent for the Agent OS: like Spring Boot monitors JVM metrics, we monitor the full agent pipeline.

## Thresholds

| Component Type | Target | WARN | ALERT |
|---------------|--------|------|-------|
| Hook | < 200ms | > 500ms | > 2s |
| Skill | < 15s | > 30s | > 60s |
| Library call | < 500ms | > 1s | > 5s |
| Safety mesh (total per call) | < 5% of session time | > 10% | > 20% |

## What We Measure

| Metric | Source | Dashboard Section |
|--------|--------|-------------------|
| Latency (p50/p95/p99) | `performance.jsonl` | LATENCY |
| Throughput (tasks/hr, calls/min) | `performance.jsonl` | THROUGHPUT |
| Hook chain overhead | `performance.jsonl` (hook: prefix) | OVERHEAD |
| Safety mesh overhead | `performance.jsonl` (gate/validator hooks) | OVERHEAD |
| Component health | Latency + error rate vs baseline | HEALTH |
| Bottlenecks | Top N by p99 latency | BOTTLENECKS |
| Efficiency (token/time/cost/error) | `performance.jsonl` + metadata | Efficiency report |

## Hook Timing (opt-in)

Hooks opt in to timing via `hooks/_lib/timing.sh`:

```bash
source "$(dirname "$0")/_lib/timing.sh"
start_timer
# ... hook logic ...
end_timer "hook-name" "true"
```

Timing is best-effort. Recording failures never affect hook execution.

## CLI

```
cos perf                    # Dashboard
cos perf --bottlenecks      # Top 5 slowest components
cos perf --overhead         # Hook/safety mesh overhead breakdown
cos perf --component <name> # Single component health
cos perf --export json      # JSON export
```

## Component Health Classification

| Status | Criteria |
|--------|----------|
| healthy | error_rate < 5%, latency < 2x baseline |
| degraded | error_rate 5-20% OR latency 2-5x baseline |
| unhealthy | error_rate > 20% OR latency > 5x baseline |

## Session Reports

A performance report is generated at session end via `PerformanceMonitor.save_session_report()`. Reports are saved to `.cognitive-os/metrics/performance-reports/`.

## Metrics File

`.cognitive-os/metrics/performance.jsonl` -- append-only, one JSON object per line:

```json
{"component":"hook:blast-radius","operation":"execute","duration_ms":42.5,"success":true,"timestamp":"2026-03-27T12:00:00Z"}
```

## Integration

| System | Integration |
|--------|-------------|
| Agent KPIs | Performance data feeds efficiency KPIs |
| Phase Timing | SDD phase timings complement per-component metrics |
| Estimation Calibrator | Historical performance informs future estimates |
| Resource Governance | Overhead alerts trigger optimization reviews |

## Contextual Trigger

This rule is always active. Performance metrics are recorded automatically by instrumented hooks and libraries.
