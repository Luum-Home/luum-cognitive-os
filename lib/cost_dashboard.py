"""Cost Dashboard — Real-time cost transparency and token economy analytics.

Provides session, daily, and monthly cost reporting with efficiency metrics,
optimization suggestions, and formatted output for both inline status and
full session reports.

Author: luum
Python 3.9+ compatible.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lib.model_catalog import ModelCatalog

# Model prices per 1M tokens (USD) — derived from ModelCatalog (single source of truth).
# Kept as a module-level dict for backward compatibility with external importers.
MODEL_PRICES: Dict[str, Dict[str, float]] = {
    alias: {"input": ModelCatalog.get(alias).input_price_per_m,
            "output": ModelCatalog.get(alias).output_price_per_m}
    for alias in ModelCatalog.all_aliases()
}

# Default daily budget (USD) — can be overridden by cognitive-os.yaml
DEFAULT_DAILY_BUDGET: float = 10.00
DEFAULT_MONTHLY_BUDGET: float = 200.00


@dataclass
class SessionCostReport:
    """Structured cost report for a single session."""

    session_id: str
    start_time: str
    duration_minutes: float
    total_cost_usd: float
    tokens_in: int
    tokens_out: int
    model_breakdown: Dict[str, float] = field(default_factory=dict)
    action_breakdown: Dict[str, float] = field(default_factory=dict)
    efficiency_score: float = 0.0
    cost_per_task: float = 0.0
    tasks_completed: int = 0
    wasted_tokens_estimate: int = 0


def _parse_timestamp(ts: str) -> Optional[datetime]:
    """Parse an ISO timestamp string, returning None on failure."""
    if not ts:
        return None
    try:
        # Handle both timezone-aware and naive timestamps
        ts_clean = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts_clean)
    except (ValueError, TypeError):
        return None


def _load_events(metrics_path: str) -> List[dict]:
    """Load all cost events from the JSONL file."""
    path = Path(metrics_path)
    if not path.exists():
        return []
    events = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return events


def _filter_events_by_date(events: List[dict], target_date: date) -> List[dict]:
    """Filter events to those occurring on a specific date (UTC).

    Compares the UTC date of timestamps against the target date.
    Callers should pass UTC-based dates for consistency (e.g.,
    ``datetime.now(timezone.utc).date()`` instead of ``date.today()``).
    """
    filtered = []
    for ev in events:
        ts = _parse_timestamp(ev.get("timestamp", ""))
        if ts:
            # Normalize to UTC for consistent comparison
            utc_date = ts.astimezone(timezone.utc).date()
            if utc_date == target_date:
                filtered.append(ev)
    return filtered


def _filter_events_by_month(events: List[dict], year: int, month: int) -> List[dict]:
    """Filter events to those occurring in a specific month (UTC)."""
    filtered = []
    for ev in events:
        ts = _parse_timestamp(ev.get("timestamp", ""))
        if ts:
            utc_ts = ts.astimezone(timezone.utc)
            if utc_ts.year == year and utc_ts.month == month:
                filtered.append(ev)
    return filtered


def _compute_event_cost(ev: dict) -> float:
    """Compute cost for a single event. Uses stored cost or calculates from tokens."""
    if "estimated_cost_usd" in ev:
        return float(ev["estimated_cost_usd"])
    model = ev.get("model", "sonnet")
    tokens_in = int(ev.get("input_tokens", 0))
    tokens_out = int(ev.get("output_tokens", 0))
    try:
        return ModelCatalog.estimate_cost(model, tokens_in, tokens_out)
    except KeyError:
        # Fallback to sonnet pricing for unknown models
        return ModelCatalog.estimate_cost("sonnet", tokens_in, tokens_out)


def _model_breakdown(events: List[dict]) -> Dict[str, float]:
    """Compute cost breakdown by model."""
    breakdown: Dict[str, float] = {}
    for ev in events:
        model = ev.get("model", "unknown")
        cost = _compute_event_cost(ev)
        breakdown[model] = breakdown.get(model, 0.0) + cost
    return breakdown


def _action_breakdown(events: List[dict]) -> Dict[str, float]:
    """Compute cost breakdown by action/agent type."""
    breakdown: Dict[str, float] = {}
    for ev in events:
        action = ev.get("agent", ev.get("action", "unknown"))
        cost = _compute_event_cost(ev)
        breakdown[action] = breakdown.get(action, 0.0) + cost
    return breakdown


def _total_tokens(events: List[dict]) -> Tuple[int, int]:
    """Sum total input and output tokens."""
    total_in = sum(int(ev.get("input_tokens", 0)) for ev in events)
    total_out = sum(int(ev.get("output_tokens", 0)) for ev in events)
    return total_in, total_out


def _count_model_calls(events: List[dict]) -> Dict[str, int]:
    """Count calls per model."""
    counts: Dict[str, int] = {}
    for ev in events:
        model = ev.get("model", "unknown")
        counts[model] = counts.get(model, 0) + 1
    return counts


class CostDashboard:
    """Real-time cost transparency dashboard.

    Reads cost events from a JSONL file and provides session, daily, and
    monthly cost reporting with efficiency metrics and optimization suggestions.
    """

    def __init__(
        self,
        metrics_path: str = ".cognitive-os/metrics/cost-events.jsonl",
        daily_budget: float = DEFAULT_DAILY_BUDGET,
        monthly_budget: float = DEFAULT_MONTHLY_BUDGET,
    ):
        self.metrics_path = metrics_path
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget

    def get_session_cost(self) -> Dict:
        """Current session cost.

        Returns dict with total_usd, tokens_in, tokens_out, model_breakdown,
        budget_remaining_pct, cost_trend, and call_count.
        """
        events = _load_events(self.metrics_path)
        total_cost = sum(_compute_event_cost(ev) for ev in events)
        tokens_in, tokens_out = _total_tokens(events)
        model_bd = _model_breakdown(events)

        today_events = _filter_events_by_date(events, datetime.now(timezone.utc).date())
        daily_cost = sum(_compute_event_cost(ev) for ev in today_events)
        budget_remaining_pct = max(
            0.0, (1.0 - daily_cost / self.daily_budget) * 100
        ) if self.daily_budget > 0 else 100.0

        return {
            "total_usd": round(total_cost, 4),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "model_breakdown": {k: round(v, 4) for k, v in model_bd.items()},
            "budget_remaining_pct": round(budget_remaining_pct, 1),
            "call_count": len(events),
            "cost_trend": "stable",
        }

    def get_daily_cost(self, day: Optional[date] = None) -> Dict:
        """Total cost for a day (UTC). Default today (UTC)."""
        target = day or datetime.now(timezone.utc).date()
        events = _load_events(self.metrics_path)
        day_events = _filter_events_by_date(events, target)
        total = sum(_compute_event_cost(ev) for ev in day_events)
        tokens_in, tokens_out = _total_tokens(day_events)
        model_bd = _model_breakdown(day_events)

        return {
            "date": target.isoformat(),
            "total_usd": round(total, 4),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "model_breakdown": {k: round(v, 4) for k, v in model_bd.items()},
            "call_count": len(day_events),
            "budget_pct": round(total / self.daily_budget * 100, 1) if self.daily_budget > 0 else 0.0,
        }

    def get_monthly_cost(self) -> Dict:
        """Monthly cost with daily breakdown and projection."""
        now = datetime.now(timezone.utc)
        events = _load_events(self.metrics_path)
        month_events = _filter_events_by_month(events, now.year, now.month)
        total = sum(_compute_event_cost(ev) for ev in month_events)
        model_bd = _model_breakdown(month_events)

        # Daily breakdown
        daily_totals: Dict[str, float] = {}
        for ev in month_events:
            ts = _parse_timestamp(ev.get("timestamp", ""))
            if ts:
                day_key = ts.date().isoformat()
                daily_totals[day_key] = daily_totals.get(day_key, 0.0) + _compute_event_cost(ev)

        # Projection: average daily cost * days in month
        days_elapsed = now.day
        avg_daily = total / days_elapsed if days_elapsed > 0 else 0.0
        import calendar
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        projected = avg_daily * days_in_month

        return {
            "month": f"{now.year}-{now.month:02d}",
            "total_usd": round(total, 4),
            "projected_usd": round(projected, 4),
            "model_breakdown": {k: round(v, 4) for k, v in model_bd.items()},
            "daily_breakdown": {k: round(v, 4) for k, v in sorted(daily_totals.items())},
            "budget_pct": round(total / self.monthly_budget * 100, 1) if self.monthly_budget > 0 else 0.0,
            "call_count": len(month_events),
        }

    def estimate_action_cost(
        self, model: str, estimated_tokens: int = 1000
    ) -> float:
        """Estimate cost of an action BEFORE executing (planning only).

        WARNING: This is a PRE-EXECUTION estimate for model selection decisions.
        For actual costs, always use real token counts from API responses.
        Never report estimates to the user as actual costs.

        Assumes a 60/40 split between input and output tokens when only
        a total token count is provided.
        """
        input_tokens = int(estimated_tokens * 0.6)
        output_tokens = int(estimated_tokens * 0.4)
        try:
            return ModelCatalog.estimate_cost(model, input_tokens, output_tokens)
        except KeyError:
            return ModelCatalog.estimate_cost("sonnet", input_tokens, output_tokens)

    def get_efficiency_metrics(self) -> Dict:
        """Token efficiency analysis.

        Returns metrics about how effectively tokens are being spent.
        """
        events = _load_events(self.metrics_path)
        if not events:
            return {
                "useful_tokens_pct": 0.0,
                "overhead_tokens_pct": 0.0,
                "wasted_tokens_pct": 0.0,
                "cost_per_file_changed": 0.0,
                "cost_per_test_written": 0.0,
                "cost_per_bug_fixed": 0.0,
            }

        total_tokens = sum(
            int(ev.get("input_tokens", 0)) + int(ev.get("output_tokens", 0))
            for ev in events
        )

        # Estimate useful vs overhead vs wasted
        successful = [ev for ev in events if ev.get("success", True)]
        failed = [ev for ev in events if not ev.get("success", True)]

        successful_tokens = sum(
            int(ev.get("input_tokens", 0)) + int(ev.get("output_tokens", 0))
            for ev in successful
        )
        failed_tokens = sum(
            int(ev.get("input_tokens", 0)) + int(ev.get("output_tokens", 0))
            for ev in failed
        )

        if total_tokens == 0:
            return {
                "useful_tokens_pct": 0.0,
                "overhead_tokens_pct": 0.0,
                "wasted_tokens_pct": 0.0,
                "cost_per_file_changed": 0.0,
                "cost_per_test_written": 0.0,
                "cost_per_bug_fixed": 0.0,
            }

        # NOTE: overhead is approximated at ~15% for rules/context loading.
        # This is a heuristic, not a measured value. Mark as approximate in output.
        # Wasted tokens = tokens from failed actions (this IS measured from real data).
        overhead_approx = total_tokens * 0.15
        useful = max(0, successful_tokens - overhead_approx)
        wasted = failed_tokens  # Real: from events with success=false

        total_cost = sum(_compute_event_cost(ev) for ev in events)
        task_count = max(1, len(events))

        return {
            "useful_tokens_pct": round(useful / total_tokens * 100, 1),
            "overhead_tokens_pct": round(overhead_approx / total_tokens * 100, 1),
            "wasted_tokens_pct": round(wasted / total_tokens * 100, 1),
            "cost_per_file_changed": round(total_cost / task_count, 4),
            "cost_per_test_written": round(total_cost / task_count, 4),
            "cost_per_bug_fixed": round(total_cost / max(1, len(failed)), 4),
        }

    def get_optimization_suggestions(self) -> List[str]:
        """Suggest ways to reduce costs based on usage patterns."""
        events = _load_events(self.metrics_path)
        suggestions: List[str] = []

        if not events:
            return suggestions

        model_bd = _model_breakdown(events)
        model_calls = _count_model_calls(events)

        # Check if opus is used for tasks that could be haiku/sonnet
        opus_names = [k for k in model_bd if "opus" in k.lower()]
        for name in opus_names:
            opus_cost = model_bd.get(name, 0.0)
            opus_calls_count = model_calls.get(name, 0)
            if opus_cost > 0.5 and opus_calls_count > 2:
                savings = opus_cost * 0.8  # sonnet is ~5x cheaper
                suggestions.append(
                    f"Use sonnet instead of opus for routine tasks "
                    f"(saves ~${savings:.2f}/session)"
                )

        # Check for high output-to-input ratio (possible over-generation)
        tokens_in, tokens_out = _total_tokens(events)
        if tokens_in > 0 and tokens_out / tokens_in > 3.0:
            suggestions.append(
                "High output-to-input ratio detected. "
                "Consider more targeted prompts to reduce output tokens."
            )

        # Check for failed events (wasted tokens)
        failed = [ev for ev in events if not ev.get("success", True)]
        if len(failed) > 3:
            wasted_cost = sum(_compute_event_cost(ev) for ev in failed)
            suggestions.append(
                f"{len(failed)} failed actions detected "
                f"(~${wasted_cost:.2f} wasted). "
                f"Review error patterns with /error-analyzer."
            )

        # Check if Engram cache could help
        if len(events) > 10:
            suggestions.append(
                "Enable Engram cache for repeated lookups "
                "(saves ~200 tokens/session on re-discoveries)"
            )

        return suggestions

    def format_compact_status(self) -> str:
        """One-line status for display during conversation."""
        data = self.get_session_cost()
        total = data["total_usd"]
        tokens = data["tokens_in"] + data["tokens_out"]

        # Determine dominant model
        model_bd = data["model_breakdown"]
        dominant = max(model_bd, key=model_bd.get) if model_bd else "none"
        # Simplify model name
        short_model = dominant.split("-")[0] if "-" in dominant else dominant

        budget_pct = 100.0 - data["budget_remaining_pct"]

        tokens_k = tokens / 1000

        return (
            f"${total:.2f} | "
            f"{tokens_k:.0f}K tokens | "
            f"{short_model} | "
            f"{budget_pct:.0f}% budget"
        )

    def format_session_report(self) -> str:
        """Full session cost report for session end."""
        data = self.get_session_cost()
        model_bd = data["model_breakdown"]
        model_calls = _count_model_calls(_load_events(self.metrics_path))
        efficiency = self.get_efficiency_metrics()
        suggestions = self.get_optimization_suggestions()

        lines = [
            "SESSION COST REPORT",
            "=" * 40,
            f"Total Cost: ${data['total_usd']:.2f}",
            f"Tokens: {data['tokens_in']:,} in / {data['tokens_out']:,} out",
            f"API Calls: {data['call_count']}",
            "",
            "Model Breakdown:",
        ]

        total_cost = data["total_usd"] or 1.0
        for model, cost in sorted(model_bd.items(), key=lambda x: -x[1]):
            pct = cost / total_cost * 100
            calls = model_calls.get(model, 0)
            lines.append(f"  {model}: ${cost:.2f} ({pct:.0f}%) -- {calls} calls")

        lines.append("")
        lines.append("Efficiency:")
        lines.append(f"  Useful tokens: {efficiency['useful_tokens_pct']:.0f}%")
        lines.append(f"  Overhead: {efficiency['overhead_tokens_pct']:.0f}%")
        lines.append(f"  Wasted: {efficiency['wasted_tokens_pct']:.0f}%")

        if suggestions:
            lines.append("")
            lines.append("Optimization Suggestions:")
            for s in suggestions:
                lines.append(f"  - {s}")

        lines.append("=" * 40)
        return "\n".join(lines)

    def format_monthly_report(self) -> str:
        """Monthly cost summary with daily chart."""
        data = self.get_monthly_cost()

        lines = [
            f"MONTHLY COST REPORT — {data['month']}",
            "=" * 40,
            f"Total: ${data['total_usd']:.2f}",
            f"Projected: ${data['projected_usd']:.2f}",
            f"Budget: {data['budget_pct']:.0f}%",
            f"API Calls: {data['call_count']}",
            "",
            "Model Breakdown:",
        ]

        for model, cost in sorted(
            data["model_breakdown"].items(), key=lambda x: -x[1]
        ):
            lines.append(f"  {model}: ${cost:.2f}")

        if data["daily_breakdown"]:
            lines.append("")
            lines.append("Daily Costs:")
            for day_str, cost in data["daily_breakdown"].items():
                bar_len = int(cost / max(data["daily_breakdown"].values()) * 20) if data["daily_breakdown"] else 0
                bar = "#" * bar_len
                lines.append(f"  {day_str}: ${cost:.2f} {bar}")

        lines.append("=" * 40)
        return "\n".join(lines)


def record_cost_event(
    model: str,
    tokens_in: int,
    tokens_out: int,
    action: str,
    success: bool = True,
    metrics_path: str = ".cognitive-os/metrics/cost-events.jsonl",
) -> None:
    """Record a cost event to the JSONL file.

    Called by hooks or lib modules after each LLM interaction.

    Args:
        model: Model identifier (e.g., "sonnet", "claude-opus-4-6").
        tokens_in: Number of input tokens consumed.
        tokens_out: Number of output tokens generated.
        action: Description of the action (e.g., "sdd-apply", "code-review").
        success: Whether the action completed successfully.
        metrics_path: Path to the JSONL file.
    """
    try:
        cost = ModelCatalog.estimate_cost(model, tokens_in, tokens_out)
    except KeyError:
        cost = ModelCatalog.estimate_cost("sonnet", tokens_in, tokens_out)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": action,
        "model": model,
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "estimated_cost_usd": round(cost, 6),
        "success": success,
    }

    path = Path(metrics_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except OSError:
        pass  # Graceful degradation — do not crash on write failure
