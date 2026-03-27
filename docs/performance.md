# Performance Monitoring — Comprehensive Guide

> Updated: 2026-03-27

## Overview

The Cognitive OS Performance Monitor is the "Micrometer/Actuator" equivalent for the Agent OS. Just as Spring Boot uses Micrometer to expose JVM metrics (heap, GC, thread pools) and Actuator to provide health endpoints, the Performance Monitor tracks every piece of the agent pipeline:

| Spring Boot Analogy | Cognitive OS Equivalent |
|---------------------|------------------------|
| JVM heap metrics | Context window usage |
| HTTP request latency | Hook/skill execution latency |
| Endpoint throughput | Tool calls/minute, tasks/hour |
| Health actuator | Component health (healthy/degraded/unhealthy) |
| Micrometer registry | `performance.jsonl` metrics file |
| `/actuator/health` | `cos perf` CLI dashboard |

## What We Measure

### 1. Latency (p50 / p95 / p99)

Per-component latency percentiles, grouped by type:

- **Hooks**: Pre/PostToolUse hooks (blast-radius, clarification-gate, etc.)
- **Skills**: SDD phases, debugging, test-driven-development, etc.
- **Libraries**: claude_executor, model_router, agent_bus, etc.

Percentiles tell you:
- **p50**: The median experience. Half of operations are faster than this.
- **p95**: The typical worst case. 19 out of 20 operations are faster.
- **p99**: The tail latency. 99 out of 100 operations are faster. High p99 indicates occasional spikes.

### 2. Throughput

How fast work is being done:

- **Tool calls/minute**: Raw throughput of all tool invocations.
- **Agent tasks/hour**: Completed agent delegations per hour.
- **Tasks/hour**: Operations with "execute"/"complete"/"run" semantics.

### 3. Overhead

The cost of the safety mesh and hook chain:

- **Total hook overhead**: Sum of all hook execution times in the session.
- **Safety mesh overhead**: Subset of hooks that are gates, validators, checkers, etc.
- **% of session time**: How much of the total session time is spent in hooks.

Target: safety mesh overhead should be under 10% of session time. If it exceeds 10%, hooks are adding too much latency and should be optimized.

### 4. Efficiency Scores

Four composite metrics (0.0 to 1.0):

| Score | Formula | What It Means |
|-------|---------|---------------|
| Token | successful_tokens / total_tokens | How much token usage produces successful results |
| Time | productive_time / total_time | How much wall-clock time is productive vs failed/wasted |
| Cost | successful_cost / total_cost | How much spend produces value |
| Error | 1.0 - (errors / total_ops) | What fraction of operations succeed |
| Composite | weighted average of all four | Overall efficiency |

### 5. Bottleneck Detection

The monitor identifies the N slowest components by p99 latency and provides suggestions:

- If p99 > 5x baseline: "Consider optimizing or caching."
- If p99 > 2x baseline: "Monitor for degradation."
- Otherwise: no suggestion (within normal range).

### 6. Component Health

Each component is classified by combining error rate and latency ratio:

| Status | Criteria | What To Do |
|--------|----------|------------|
| healthy | error_rate < 5% AND latency < 2x baseline | Nothing. All good. |
| degraded | error_rate 5-20% OR latency 2-5x baseline | Monitor. May need attention soon. |
| unhealthy | error_rate > 20% OR latency > 5x baseline | Investigate immediately. |

Baseline latencies:
- Hooks: 500ms
- Skills: 30,000ms (30s)
- Libraries: 1,000ms (1s)

## How to Read the Dashboard

Run `cos perf` to see the ASCII dashboard:

```
+==================================================+
|     COGNITIVE OS PERFORMANCE DASHBOARD            |
+==================================================+
|                                                   |
|  LATENCY (p50 / p95 / p99)                       |
|  +-- Hooks:     12ms / 45ms / 120ms              |
|  +-- Skills:    2.1s / 8.5s / 15.2s              |
|  +-- Libs:      5ms  / 22ms / 89ms               |
|  +-- Total:     2.3s / 9.1s / 16.0s              |
|                                                   |
|  THROUGHPUT                                       |
|  +-- Tool calls:    45.0/min                      |
|  +-- Agent tasks:   8.0/hour                      |
|  +-- Tasks:         12.0/hour                     |
|                                                   |
|  OVERHEAD                                         |
|  +-- Safety mesh:   340ms                         |
|  +-- Hook chain:    520ms                         |
|  +-- Session pct:   6.4%                          |
|                                                   |
|  BOTTLENECKS                                      |
|  1. hook:auto-repair (p99: 890ms)                 |
|  2. hook:completion-gate (p99: 650ms)             |
|  3. lib:claude_executor (p99: 12500ms)            |
|                                                   |
|  HEALTH: 45 healthy  3 degraded  0 unhealthy      |
+==================================================+
```

### Reading the sections:

- **LATENCY**: If hook p99 > 500ms, some hooks are slow. If skill p95 > 30s, skills may need model routing optimization.
- **THROUGHPUT**: Low tool calls/minute may indicate blocking waits. Low agent tasks/hour may indicate complex tasks.
- **OVERHEAD**: Session pct > 10% means hooks are adding significant overhead. Check the hooks_breakdown via `cos perf --overhead`.
- **BOTTLENECKS**: The slowest components. Focus optimization here for maximum impact.
- **HEALTH**: Quick summary of component statuses across the session.

## How to Identify and Fix Bottlenecks

### Step 1: Find the bottleneck

```bash
cos perf --bottlenecks
```

### Step 2: Inspect the component

```bash
cos perf --component hook:auto-repair
```

### Step 3: Diagnose

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| High p99, normal p50 | Occasional spikes (cold start, large input) | Add caching or fast-path for common cases |
| High p50 | Component is consistently slow | Optimize algorithm or reduce work scope |
| High error rate | Component frequently fails | Fix underlying bug, add retry logic |
| Degraded health | Multiple symptoms | Prioritize the dominant contributor |

### Step 4: Fix and measure

After fixing, check that the bottleneck has improved:

```bash
cos perf --component hook:auto-repair
```

## Cost of Monitoring

The performance monitor itself adds minimal overhead:

- **Recording a metric**: ~0.1ms (in-memory append + async file write).
- **JSONL persistence**: ~0.5ms per write (buffered I/O).
- **Dashboard generation**: ~5ms (in-memory aggregation).
- **Disk usage**: ~100 bytes per metric entry. A busy session with 1000 tool calls uses ~100KB.

The monitoring overhead is orders of magnitude smaller than the operations being monitored.

## Instrumenting Hooks

To add timing to a hook, source `hooks/_lib/timing.sh`:

```bash
#!/usr/bin/env bash
source "$(dirname "$0")/_lib/common.sh"
source "$(dirname "$0")/_lib/timing.sh"

start_timer

# ... hook logic here ...

end_timer "my-hook-name" "true"
```

The `end_timer` function records the duration to `performance.jsonl`. If Python is unavailable or recording fails, the hook continues normally.

## Instrumenting Python Libraries

Use the `time_operation` context manager:

```python
from lib.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor()

with monitor.time_operation("lib:my_module", "process") as timer:
    result = do_expensive_work()

# timer.duration_ms is available after the block
```

Or record manually:

```python
monitor.record("lib:my_module", "process", duration_ms=42.5, success=True, tokens=1500)
```

## Integration with Existing Systems

### Agent KPIs (`rules/agent-kpis.md`)

Performance data feeds into the Agent Efficiency and Resource Efficiency OKRs. High overhead or low throughput triggers KPI alerts.

### Phase Timing (`lib/phase_timing.py`)

Phase timing tracks SDD phase durations. Performance monitoring complements it with per-component granularity within each phase.

### Estimation Calibrator (`lib/estimation_calibrator.py`)

Historical performance data (actual durations) feeds calibration. Over time, estimates become more accurate as the calibrator adjusts for consistent over/under-estimates.

### Resource Governance (`rules/resource-governance.md`)

When overhead exceeds thresholds:
- 10% session time: WARN, suggest optimization.
- 20% session time: ALERT, consider disabling non-critical hooks.

## Configuration

In `cognitive-os.yaml`:

```yaml
performance:
  enabled: true
  metrics_file: performance.jsonl
  thresholds:
    hook_warn_ms: 500
    hook_alert_ms: 2000
    skill_warn_ms: 30000
    skill_alert_ms: 60000
    overhead_warn_pct: 10
    overhead_alert_pct: 20
  session_report: true    # Generate report at session end
```
