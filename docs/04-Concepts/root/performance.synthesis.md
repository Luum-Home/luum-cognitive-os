---
type: concept-synthesis
source: docs/04-Concepts/root/performance.md
---

## What it is
The Cognitive OS Performance Monitor — a Spring-Boot-Micrometer/Actuator equivalent that tracks latency, throughput, overhead, efficiency, bottlenecks, and component health across hooks, skills, and libraries via `performance.jsonl` and the `cos perf` CLI dashboard.

## Key mechanics
- Metrics tracked: (1) Latency p50/p95/p99 per component type (hooks, skills, libs); (2) Throughput — tool calls/min, agent tasks/hr, tasks/hr; (3) Overhead — total hook overhead, safety mesh overhead, % of session time (target <10%); (4) Efficiency scores 0.0-1.0 — token (successful/total tokens), time (productive/total time), cost (successful/total cost), error (1 - errors/total ops), composite (weighted average); (5) Bottleneck detection — flags top-N slowest by p99, "consider optimizing/caching" if p99 > 5x baseline, "monitor" if > 2x baseline; (6) Component health — healthy (error <5% AND latency <2x baseline), degraded (error 5-20% OR latency 2-5x), unhealthy (error >20% OR latency >5x).
- Baseline latencies: hooks 500ms, skills 30,000ms (30s), libs 1,000ms (1s).
- CLI: `cos perf` (full dashboard), `cos perf --bottlenecks`, `cos perf --component <name>`, `cos perf --overhead`.
- Instrumentation: bash hooks source `hooks/_lib/timing.sh` (`start_timer`/`end_timer`); Python libs use `PerformanceMonitor().time_operation()` context manager or `.record()` directly.
- Monitoring's own overhead: ~0.1ms per metric record, ~0.5ms JSONL write, ~5ms dashboard generation, ~100 bytes/entry (~100KB for 1000 tool calls).
- Config in `cognitive-os.yaml -> performance`: thresholds hook_warn_ms(500)/hook_alert_ms(2000)/skill_warn_ms(30000)/skill_alert_ms(60000)/overhead_warn_pct(10)/overhead_alert_pct(20).

## Relations & where used
Feeds Agent KPIs (`rules/agent-kpis.md`) Agent Efficiency and Resource Efficiency OKRs. Complements `lib/phase_timing.py` (SDD phase durations) with per-component granularity. Feeds `lib/estimation_calibrator.py` historical accuracy calibration. Integrates with `rules/resource-governance.md`: overhead >10% session time = WARN, >20% = ALERT (consider disabling non-critical hooks).

## Status / caveats
No explicit status field stated; presented as an active/available subsystem. No caveats or known gaps noted in the source doc.
