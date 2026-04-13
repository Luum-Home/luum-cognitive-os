# scope: both
"""Performance Monitor — latency, throughput, and efficiency tracking for Cognitive OS.

The "Micrometer/Actuator" equivalent for Agent OS: like Spring Boot monitors
JVM metrics, we monitor every piece of the agent pipeline — hooks, skills, libs,
and the safety mesh.

Tracks:
- Latency (p50/p95/p99) per component
- Throughput (tasks/hour, tool calls/minute)
- Overhead (hook chain + safety mesh as % of session time)
- Efficiency (token, time, cost, error composites)
- Bottleneck detection with suggestions
- Per-component health (healthy/degraded/unhealthy)

Python 3.9+ compatible. No external dependencies.
Author: luum
"""

from __future__ import annotations

import json
import os
import statistics
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple


@dataclass
class PerformanceMetric:
    """A single performance measurement."""

    component: str          # "hook:clarification-gate", "skill:sdd-apply", "lib:claude_executor"
    operation: str          # "execute", "parse", "validate", etc.
    duration_ms: float
    success: bool
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)  # tokens, model, phase, etc.


# Baseline latency thresholds (ms) by component prefix.
# Used for health classification.
_BASELINE_THRESHOLDS: Dict[str, float] = {
    "hook": 500.0,
    "skill": 30000.0,
    "lib": 1000.0,
}


def _iso_now() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _component_prefix(component: str) -> str:
    """Extract the prefix from a component name (e.g., 'hook' from 'hook:blast-radius')."""
    if ":" in component:
        return component.split(":")[0]
    return component


def _baseline_for(component: str) -> float:
    """Get the baseline latency threshold for a component."""
    prefix = _component_prefix(component)
    return _BASELINE_THRESHOLDS.get(prefix, 1000.0)


class PerformanceMonitor:
    """Tracks latency, throughput, and efficiency of every Cognitive OS component.

    Persists metrics to a JSONL file and keeps in-memory session metrics
    for fast querying during the current session.
    """

    def __init__(self, metrics_path: str = ".cognitive-os/metrics/performance.jsonl"):
        self.metrics_path = metrics_path
        self._session_metrics: List[PerformanceMetric] = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(
        self,
        component: str,
        operation: str,
        duration_ms: float,
        success: bool = True,
        **metadata: Any,
    ) -> None:
        """Record a single performance measurement.

        Args:
            component: Component identifier (e.g., "hook:blast-radius").
            operation: Operation name (e.g., "execute").
            duration_ms: Duration in milliseconds.
            success: Whether the operation succeeded.
            **metadata: Extra key-value pairs (tokens, model, phase, etc.).
        """
        metric = PerformanceMetric(
            component=component,
            operation=operation,
            duration_ms=round(duration_ms, 2),
            success=success,
            timestamp=_iso_now(),
            metadata=dict(metadata),
        )

        with self._lock:
            self._session_metrics.append(metric)

        self._persist(metric)

    @contextmanager
    def time_operation(
        self, component: str, operation: str, **metadata: Any
    ) -> Iterator["_Timer"]:
        """Context manager for timing operations.

        Usage::

            with monitor.time_operation("hook:blast-radius", "execute") as timer:
                # ... do work ...
            # automatically records duration; timer.duration_ms is available
        """
        timer = _Timer()
        try:
            yield timer
        except Exception:
            timer.stop()
            self.record(
                component, operation, timer.duration_ms, success=False, **metadata
            )
            raise
        else:
            timer.stop()
            self.record(
                component, operation, timer.duration_ms, success=True, **metadata
            )

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def get_percentiles(
        self, component: str, window_minutes: int = 60
    ) -> Dict[str, Any]:
        """Calculate p50, p95, p99 latency for a component.

        Args:
            component: Component identifier.
            window_minutes: Look-back window in minutes.

        Returns:
            Dict with p50_ms, p95_ms, p99_ms, count, error_rate.
        """
        metrics = self._filter(component=component, window_minutes=window_minutes)
        if not metrics:
            return {
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "count": 0,
                "error_rate": 0.0,
            }

        durations = sorted(m.duration_ms for m in metrics)
        errors = sum(1 for m in metrics if not m.success)

        return {
            "p50_ms": round(_percentile(durations, 50), 2),
            "p95_ms": round(_percentile(durations, 95), 2),
            "p99_ms": round(_percentile(durations, 99), 2),
            "count": len(metrics),
            "error_rate": round(errors / len(metrics), 4) if metrics else 0.0,
        }

    def get_overhead_report(self) -> Dict[str, Any]:
        """Calculate total overhead added by hooks/rules/safety mesh.

        Returns:
            Dict with total_hook_overhead_ms, hooks_breakdown, safety_mesh_overhead_ms,
            pct_of_session_time.
        """
        hook_metrics = [m for m in self._session_metrics if m.component.startswith("hook:")]
        skill_metrics = [m for m in self._session_metrics if m.component.startswith("skill:")]

        # Hook breakdown
        hooks_breakdown: Dict[str, float] = {}
        for m in hook_metrics:
            hooks_breakdown[m.component] = hooks_breakdown.get(m.component, 0.0) + m.duration_ms

        total_hook_ms = sum(hooks_breakdown.values())

        # Safety mesh hooks (gates, validators, checkers)
        safety_keywords = (
            "gate", "validator", "checker", "detector", "guard", "scanner",
            "interceptor", "tracker",
        )
        safety_ms = sum(
            dur for comp, dur in hooks_breakdown.items()
            if any(kw in comp for kw in safety_keywords)
        )

        # Total session time = sum of all operation durations
        total_session_ms = sum(m.duration_ms for m in self._session_metrics)

        pct = (total_hook_ms / total_session_ms * 100.0) if total_session_ms > 0 else 0.0

        return {
            "total_hook_overhead_ms": round(total_hook_ms, 2),
            "hooks_breakdown": {k: round(v, 2) for k, v in hooks_breakdown.items()},
            "safety_mesh_overhead_ms": round(safety_ms, 2),
            "pct_of_session_time": round(pct, 2),
        }

    def get_throughput(self, window_minutes: int = 60) -> Dict[str, Any]:
        """Tasks/hour, tool_calls/minute, agent_completions/hour.

        Args:
            window_minutes: Look-back window.

        Returns:
            Dict with tasks_per_hour, tool_calls_per_minute, agent_completions_per_hour.
        """
        metrics = self._filter(window_minutes=window_minutes)
        if not metrics:
            return {
                "tasks_per_hour": 0.0,
                "tool_calls_per_minute": 0.0,
                "agent_completions_per_hour": 0.0,
            }

        hours = max(window_minutes / 60.0, 1 / 60.0)  # avoid division by zero
        minutes = max(float(window_minutes), 1.0)

        tool_calls = len(metrics)
        agent_completions = sum(
            1 for m in metrics
            if m.component.startswith("skill:") or m.component.startswith("agent:")
        )
        tasks = sum(
            1 for m in metrics
            if m.operation in ("execute", "complete", "run")
        )

        return {
            "tasks_per_hour": round(tasks / hours, 2),
            "tool_calls_per_minute": round(tool_calls / minutes, 2),
            "agent_completions_per_hour": round(agent_completions / hours, 2),
        }

    def get_efficiency_score(self) -> Dict[str, float]:
        """Composite efficiency metric.

        Returns:
            Dict with token, time, cost, error, composite scores (0.0-1.0).
        """
        metrics = self._session_metrics
        if not metrics:
            return {
                "token": 0.0,
                "time": 0.0,
                "cost": 0.0,
                "error": 0.0,
                "composite": 0.0,
            }

        # Token efficiency: ratio of successful token usage
        total_tokens = 0
        successful_tokens = 0
        for m in metrics:
            tokens = m.metadata.get("tokens", 0)
            total_tokens += tokens
            if m.success:
                successful_tokens += tokens
        token_eff = (successful_tokens / total_tokens) if total_tokens > 0 else 1.0

        # Time efficiency: productive (successful) time / total time
        total_time = sum(m.duration_ms for m in metrics)
        productive_time = sum(m.duration_ms for m in metrics if m.success)
        time_eff = (productive_time / total_time) if total_time > 0 else 1.0

        # Cost efficiency: successful ops / total ops weighted by cost
        total_cost = 0.0
        successful_cost = 0.0
        for m in metrics:
            cost = m.metadata.get("cost_usd", 0.0)
            total_cost += cost
            if m.success:
                successful_cost += cost
        cost_eff = (successful_cost / total_cost) if total_cost > 0 else 1.0

        # Error efficiency: 1.0 - error_rate
        errors = sum(1 for m in metrics if not m.success)
        error_eff = 1.0 - (errors / len(metrics))

        composite = (
            token_eff * 0.25
            + time_eff * 0.25
            + cost_eff * 0.25
            + error_eff * 0.25
        )

        return {
            "token": round(token_eff, 4),
            "time": round(time_eff, 4),
            "cost": round(cost_eff, 4),
            "error": round(error_eff, 4),
            "composite": round(composite, 4),
        }

    def get_bottlenecks(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Identify the N slowest components.

        Args:
            top_n: Number of bottlenecks to return.

        Returns:
            List of dicts with component, avg_ms, p99_ms, call_count, suggestion.
        """
        # Group by component
        by_component: Dict[str, List[float]] = {}
        for m in self._session_metrics:
            by_component.setdefault(m.component, []).append(m.duration_ms)

        if not by_component:
            return []

        bottlenecks: List[Dict[str, Any]] = []
        for comp, durations in by_component.items():
            sorted_d = sorted(durations)
            avg = statistics.mean(sorted_d)
            p99 = _percentile(sorted_d, 99)
            baseline = _baseline_for(comp)

            suggestion = ""
            if p99 > baseline * 5:
                suggestion = f"p99 is {p99 / baseline:.1f}x baseline ({baseline:.0f}ms). Consider optimizing or caching."
            elif p99 > baseline * 2:
                suggestion = f"p99 is {p99 / baseline:.1f}x baseline. Monitor for degradation."

            bottlenecks.append({
                "component": comp,
                "avg_ms": round(avg, 2),
                "p99_ms": round(p99, 2),
                "call_count": len(sorted_d),
                "suggestion": suggestion,
            })

        # Sort by p99 descending
        bottlenecks.sort(key=lambda b: b["p99_ms"], reverse=True)
        return bottlenecks[:top_n]

    def get_component_health(self, component: str) -> Dict[str, Any]:
        """Health status of a single component.

        Returns:
            Dict with status (healthy/degraded/unhealthy), avg_latency_ms,
            error_rate, last_success, suggestion.

        Thresholds:
            healthy:   error_rate < 5%, latency within 2x baseline
            degraded:  error_rate 5-20% or latency 2-5x baseline
            unhealthy: error_rate > 20% or latency > 5x baseline
        """
        metrics = [m for m in self._session_metrics if m.component == component]
        if not metrics:
            return {
                "status": "unknown",
                "avg_latency_ms": 0.0,
                "error_rate": 0.0,
                "last_success": None,
                "suggestion": "No data available for this component.",
            }

        durations = [m.duration_ms for m in metrics]
        avg_latency = statistics.mean(durations)
        errors = sum(1 for m in metrics if not m.success)
        error_rate = errors / len(metrics)
        baseline = _baseline_for(component)

        # Find last successful operation
        successes = [m for m in metrics if m.success]
        last_success = successes[-1].timestamp if successes else None

        # Classify health
        latency_ratio = avg_latency / baseline if baseline > 0 else 1.0

        if error_rate > 0.20 or latency_ratio > 5.0:
            status = "unhealthy"
        elif error_rate > 0.05 or latency_ratio > 2.0:
            status = "degraded"
        else:
            status = "healthy"

        suggestion = ""
        if status == "unhealthy":
            if error_rate > 0.20:
                suggestion = f"Error rate {error_rate:.0%} exceeds 20% threshold. Investigate failures."
            else:
                suggestion = f"Latency {avg_latency:.0f}ms is {latency_ratio:.1f}x baseline. Consider optimization."
        elif status == "degraded":
            if error_rate > 0.05:
                suggestion = f"Error rate {error_rate:.0%} is elevated. Monitor for further degradation."
            else:
                suggestion = f"Latency {avg_latency:.0f}ms is {latency_ratio:.1f}x baseline. Watch for trends."

        return {
            "status": status,
            "avg_latency_ms": round(avg_latency, 2),
            "error_rate": round(error_rate, 4),
            "last_success": last_success,
            "suggestion": suggestion,
        }

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def format_dashboard(self) -> str:
        """ASCII dashboard for terminal display."""
        lines: List[str] = []

        # Header
        lines.append("")
        lines.append("+" + "=" * 50 + "+")
        lines.append("|" + "COGNITIVE OS PERFORMANCE DASHBOARD".center(50) + "|")
        lines.append("+" + "=" * 50 + "+")
        lines.append("|" + " " * 50 + "|")

        # Latency section
        hook_pct = self._aggregate_percentiles("hook")
        skill_pct = self._aggregate_percentiles("skill")
        lib_pct = self._aggregate_percentiles("lib")

        lines.append("|  LATENCY (p50 / p95 / p99)" + " " * 23 + "|")
        lines.append(self._fmt_latency_line("Hooks", hook_pct))
        lines.append(self._fmt_latency_line("Skills", skill_pct))
        lines.append(self._fmt_latency_line("Libs", lib_pct))

        # Total latency
        all_durations = sorted(m.duration_ms for m in self._session_metrics)
        if all_durations:
            total_pct = {
                "p50_ms": _percentile(all_durations, 50),
                "p95_ms": _percentile(all_durations, 95),
                "p99_ms": _percentile(all_durations, 99),
            }
        else:
            total_pct = {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
        lines.append(self._fmt_latency_line("Total", total_pct))

        lines.append("|" + " " * 50 + "|")

        # Throughput section
        tp = self.get_throughput()
        lines.append("|  THROUGHPUT" + " " * 38 + "|")
        lines.append(
            f"|  +-- Tool calls:    {tp['tool_calls_per_minute']:.1f}/min".ljust(51)
            + "|"
        )
        lines.append(
            f"|  +-- Agent tasks:   {tp['agent_completions_per_hour']:.1f}/hour".ljust(
                51
            )
            + "|"
        )
        lines.append(
            f"|  +-- Tasks:         {tp['tasks_per_hour']:.1f}/hour".ljust(51) + "|"
        )

        lines.append("|" + " " * 50 + "|")

        # Overhead section
        oh = self.get_overhead_report()
        lines.append("|  OVERHEAD" + " " * 40 + "|")
        lines.append(
            f"|  +-- Safety mesh:   {oh['safety_mesh_overhead_ms']:.0f}ms".ljust(51)
            + "|"
        )
        lines.append(
            f"|  +-- Hook chain:    {oh['total_hook_overhead_ms']:.0f}ms".ljust(51)
            + "|"
        )
        lines.append(
            f"|  +-- Session pct:   {oh['pct_of_session_time']:.1f}%".ljust(51) + "|"
        )

        lines.append("|" + " " * 50 + "|")

        # Bottlenecks section
        bottlenecks = self.get_bottlenecks(top_n=3)
        lines.append("|  BOTTLENECKS" + " " * 37 + "|")
        if bottlenecks:
            for i, b in enumerate(bottlenecks, 1):
                line = f"|  {i}. {b['component']} (p99: {b['p99_ms']:.0f}ms)"
                lines.append(line.ljust(51) + "|")
        else:
            lines.append("|  (no data)" + " " * 39 + "|")

        lines.append("|" + " " * 50 + "|")

        # Health summary
        health_counts = self._health_summary()
        health_line = (
            f"|  HEALTH: {health_counts['healthy']} healthy  "
            f"{health_counts['degraded']} degraded  "
            f"{health_counts['unhealthy']} unhealthy"
        )
        lines.append(health_line.ljust(51) + "|")
        lines.append("+" + "=" * 50 + "+")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_session_report(self) -> str:
        """Save session performance report to metrics/performance-reports/.

        Returns:
            Path to the saved report file.
        """
        report_dir = os.path.join(
            os.path.dirname(self.metrics_path), "performance-reports"
        )
        os.makedirs(report_dir, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        report_path = os.path.join(report_dir, f"session-{ts}.txt")

        dashboard = self.format_dashboard()

        # Build detailed report
        sections: List[str] = [
            f"Performance Report — {_iso_now()}",
            "=" * 60,
            "",
            dashboard,
            "",
            "## Efficiency Scores",
            json.dumps(self.get_efficiency_score(), indent=2),
            "",
            "## Overhead Report",
            json.dumps(self.get_overhead_report(), indent=2),
            "",
            "## Top Bottlenecks",
            json.dumps(self.get_bottlenecks(), indent=2),
            "",
            f"## Total Metrics Recorded: {len(self._session_metrics)}",
        ]

        content = "\n".join(sections)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

        return report_path

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _persist(self, metric: PerformanceMetric) -> None:
        """Append metric to JSONL file (best effort)."""
        try:
            parent = os.path.dirname(self.metrics_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            record = {
                "component": metric.component,
                "operation": metric.operation,
                "duration_ms": metric.duration_ms,
                "success": metric.success,
                "timestamp": metric.timestamp,
            }
            if metric.metadata:
                record["metadata"] = metric.metadata

            with open(self.metrics_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except OSError:
            pass  # Best effort — don't fail the caller

    def _filter(
        self,
        component: Optional[str] = None,
        window_minutes: int = 60,
    ) -> List[PerformanceMetric]:
        """Filter session metrics by component and time window."""
        cutoff = datetime.now(timezone.utc).timestamp() - (window_minutes * 60)

        result: List[PerformanceMetric] = []
        for m in self._session_metrics:
            # Parse timestamp
            try:
                ts = datetime.strptime(m.timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                )
                if ts.timestamp() < cutoff:
                    continue
            except (ValueError, TypeError):
                pass  # Include if timestamp can't be parsed

            if component and m.component != component:
                continue

            result.append(m)
        return result

    def _aggregate_percentiles(self, prefix: str) -> Dict[str, float]:
        """Aggregate percentiles across all components with a given prefix."""
        durations = sorted(
            m.duration_ms
            for m in self._session_metrics
            if m.component.startswith(f"{prefix}:")
        )
        if not durations:
            return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
        return {
            "p50_ms": _percentile(durations, 50),
            "p95_ms": _percentile(durations, 95),
            "p99_ms": _percentile(durations, 99),
        }

    def _fmt_latency_line(self, label: str, pct: Dict[str, float]) -> str:
        """Format a single latency line for the dashboard."""
        p50 = _fmt_ms(pct["p50_ms"])
        p95 = _fmt_ms(pct["p95_ms"])
        p99 = _fmt_ms(pct["p99_ms"])
        inner = f"|  +-- {label}:{' ' * max(1, 10 - len(label))}{p50} / {p95} / {p99}"
        return inner.ljust(51) + "|"

    def _health_summary(self) -> Dict[str, int]:
        """Count components by health status."""
        components = set(m.component for m in self._session_metrics)
        counts = {"healthy": 0, "degraded": 0, "unhealthy": 0, "unknown": 0}
        for comp in components:
            health = self.get_component_health(comp)
            status = health["status"]
            counts[status] = counts.get(status, 0) + 1
        return counts


class _Timer:
    """Internal timer helper for the time_operation context manager."""

    def __init__(self) -> None:
        self._start = time.monotonic()
        self._end: Optional[float] = None

    def stop(self) -> None:
        if self._end is None:
            self._end = time.monotonic()

    @property
    def duration_ms(self) -> float:
        end = self._end if self._end is not None else time.monotonic()
        return round((end - self._start) * 1000.0, 2)


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------


def _percentile(sorted_values: List[float], pct: float) -> float:
    """Calculate the given percentile from a sorted list of values.

    Uses linear interpolation between data points.
    """
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]

    k = (pct / 100.0) * (len(sorted_values) - 1)
    f = int(k)
    c = f + 1

    if c >= len(sorted_values):
        return sorted_values[-1]

    frac = k - f
    return sorted_values[f] + frac * (sorted_values[c] - sorted_values[f])


def _fmt_ms(ms: float) -> str:
    """Format milliseconds for dashboard display."""
    if ms == 0.0:
        return "0ms"
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms / 1000.0:.1f}s"


# ------------------------------------------------------------------
# Convenience functions for hooks
# ------------------------------------------------------------------


def measure_hook(hook_name: str, duration_ms: float, success: bool = True) -> None:
    """Record a hook execution time.

    Designed to be called from bash hooks via a Python one-liner::

        python3 -c "from lib.performance_monitor import measure_hook; \\
                     measure_hook('blast-radius', 42, True)"
    """
    monitor = PerformanceMonitor()
    monitor.record(f"hook:{hook_name}", "execute", duration_ms, success)
