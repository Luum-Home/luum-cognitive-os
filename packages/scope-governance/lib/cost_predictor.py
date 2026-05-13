# SCOPE: both
# scope: both
"""Cost Predictor — Predictive cost engine based on historical task data.

Connects existing components (cost_dashboard, estimation_calibrator, error_matching)
into a predictive cost engine that uses REAL historical data to estimate future
task costs with confidence levels and calibration adjustments.

Author: luum
Python 3.9+ compatible.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Default model prices — used ONLY when no historical data exists.
# The CostPredictor calculates REAL prices from actual API responses.
# These defaults should be updated when providers change pricing.
# Source: https://docs.anthropic.com/en/docs/about-claude/models
# Last verified: 2026-03-27
# ---------------------------------------------------------------------------
DEFAULT_MODEL_PRICES: Dict[str, Dict[str, float]] = {
    "opus": {"input": 15.00, "output": 75.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "haiku": {"input": 0.25, "output": 1.25},
    "claude-haiku-3.5": {"input": 0.25, "output": 1.25},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    "deepseek-r1": {"input": 0.55, "output": 2.19},
    "llama-3-70b": {"input": 0.0, "output": 0.0},
    "qwen-3-32b": {"input": 0.0, "output": 0.0},
}

# SDD phases in execution order
SDD_PHASES = [
    "explore", "propose", "spec", "design", "tasks", "apply", "verify",
]

# Default model routing per phase (matches rules/model-routing.md)
PHASE_MODEL_DEFAULTS: Dict[str, str] = {
    "explore": "sonnet",
    "propose": "opus",
    "spec": "sonnet",
    "design": "opus",
    "tasks": "sonnet",
    "apply": "sonnet",
    "verify": "sonnet",
    "archive": "haiku",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class HistoricalTask:
    """A completed task recorded for future prediction reference."""

    description: str
    task_type: str  # feature, bugfix, refactor, docs, research
    phases_executed: List[str] = field(default_factory=list)
    total_cost_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    models_used: Dict[str, int] = field(default_factory=dict)
    duration_minutes: float = 0.0
    files_changed: int = 0
    timestamp: str = ""


@dataclass
class CostPrediction:
    """Result of a cost prediction."""

    estimated_cost_min: float = 0.0
    estimated_cost_max: float = 0.0
    estimated_cost_mid: float = 0.0
    confidence: float = 0.0  # 0.0-1.0
    basis: str = "no_data"  # "historical" | "model_routing" | "no_data"
    similar_tasks: List[Dict] = field(default_factory=list)
    calibration_applied: float = 1.0  # multiplier applied (1.0 = no adjustment)
    breakdown: Dict[str, float] = field(default_factory=dict)
    recommendation: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_jsonl(path: str) -> List[dict]:
    """Load all JSON objects from a JSONL file."""
    p = Path(path)
    if not p.exists():
        return []
    entries: List[dict] = []
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return entries


def _parse_timestamp(ts: str) -> Optional[datetime]:
    """Parse an ISO timestamp string, returning None on failure."""
    if not ts:
        return None
    try:
        ts_clean = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts_clean)
    except (ValueError, TypeError):
        return None


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """Word-level Jaccard similarity between two strings.

    Tokenizes both strings into word sets and returns the Jaccard index
    (intersection / union). Returns 0.0 if either string is empty.
    """
    if not text_a or not text_b:
        return 0.0

    # Normalize: lowercase, strip punctuation-like chars, split
    norm_a = re.sub(r"[^\w\s]", " ", text_a.lower())
    norm_b = re.sub(r"[^\w\s]", " ", text_b.lower())

    words_a = set(norm_a.split())
    words_b = set(norm_b.split())

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union) if union else 0.0


def _dict_to_historical_task(d: dict) -> HistoricalTask:
    """Convert a dict (from JSONL) to a HistoricalTask."""
    return HistoricalTask(
        description=d.get("description", ""),
        task_type=d.get("task_type", "feature"),
        phases_executed=d.get("phases_executed", []),
        total_cost_usd=float(d.get("total_cost_usd", 0.0)),
        tokens_in=int(d.get("tokens_in", 0)),
        tokens_out=int(d.get("tokens_out", 0)),
        models_used=d.get("models_used", {}),
        duration_minutes=float(d.get("duration_minutes", 0.0)),
        files_changed=int(d.get("files_changed", 0)),
        timestamp=d.get("timestamp", ""),
    )


# ---------------------------------------------------------------------------
# CostPredictor
# ---------------------------------------------------------------------------


class CostPredictor:
    """Predictive cost engine based on historical task data.

    Uses word-level Jaccard similarity to find historically similar tasks,
    applies calibration factors from estimation_calibrator, and provides
    cost predictions with confidence levels.
    """

    def __init__(
        self,
        history_path: str = ".cognitive-os/metrics/task-history.jsonl",
        cost_events_path: str = ".cognitive-os/metrics/cost-events.jsonl",
    ):
        self.history_path = history_path
        self.cost_events_path = cost_events_path

    def predict(
        self,
        task_description: str,
        task_type: str = "feature",
    ) -> CostPrediction:
        """Predict cost based on historical data + calibration.

        Strategy:
        1. Find similar historical tasks (Jaccard similarity >= 0.5)
        2. If found: use weighted average of similar task costs
        3. Apply calibration factor from estimation_calibrator
        4. If no history: fall back to model-routing based estimate
        5. Return range (min-max) with confidence level

        Confidence levels:
        - 5+ similar tasks with >0.7 similarity: HIGH (0.8-0.9)
        - 2-4 similar tasks with >0.5 similarity: MEDIUM (0.5-0.7)
        - 1 similar task: LOW (0.3-0.5)
        - No history: VERY LOW (0.1-0.2) -- model-based estimate only
        """
        similar = self.find_similar_tasks(task_description, min_similarity=0.5)

        if not similar:
            return self._predict_from_model_routing(task_type)

        # Weighted average: weight = similarity^2
        total_weight = 0.0
        weighted_cost = 0.0
        similar_dicts: List[Dict] = []

        for task, sim in similar:
            weight = sim * sim
            weighted_cost += task.total_cost_usd * weight
            total_weight += weight
            similar_dicts.append({
                "description": task.description,
                "cost": task.total_cost_usd,
                "similarity": round(sim, 2),
            })

        if total_weight <= 0:
            return self._predict_from_model_routing(task_type)

        mid_cost = weighted_cost / total_weight

        # Apply calibration
        calibration = self._get_calibration_factor()
        mid_cost *= calibration

        # Compute range
        costs = [t.total_cost_usd for t, _ in similar]
        cost_min = min(costs) * calibration
        cost_max = max(costs) * calibration

        # Ensure min < mid < max
        if cost_min > mid_cost:
            cost_min = mid_cost * 0.7
        if cost_max < mid_cost:
            cost_max = mid_cost * 1.5

        # Confidence
        confidence = self._calculate_confidence(similar)

        # Phase breakdown from history
        breakdown = self.estimate_per_phase(task_type)

        # Recommendation
        recommendation = self._generate_recommendation(breakdown, mid_cost)

        return CostPrediction(
            estimated_cost_min=round(cost_min, 2),
            estimated_cost_max=round(cost_max, 2),
            estimated_cost_mid=round(mid_cost, 2),
            confidence=round(confidence, 2),
            basis="historical",
            similar_tasks=similar_dicts,
            calibration_applied=round(calibration, 2),
            breakdown=breakdown,
            recommendation=recommendation,
        )

    def record_completed_task(self, task: HistoricalTask) -> None:
        """Record a completed task for future predictions.

        Called at the end of each SDD pipeline or significant task.
        Appends to task-history.jsonl.
        """
        if not task.timestamp:
            task.timestamp = datetime.now(timezone.utc).isoformat()

        entry = {
            "description": task.description,
            "task_type": task.task_type,
            "phases_executed": task.phases_executed,
            "total_cost_usd": round(task.total_cost_usd, 6),
            "tokens_in": task.tokens_in,
            "tokens_out": task.tokens_out,
            "models_used": task.models_used,
            "duration_minutes": round(task.duration_minutes, 2),
            "files_changed": task.files_changed,
            "timestamp": task.timestamp,
        }

        path = Path(self.history_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass  # Graceful degradation

    def find_similar_tasks(
        self,
        description: str,
        min_similarity: float = 0.5,
        max_results: int = 5,
    ) -> List[Tuple[HistoricalTask, float]]:
        """Find historically similar tasks using word-level Jaccard similarity.

        Returns list of (task, similarity_score) sorted by similarity descending.
        """
        history = _load_jsonl(self.history_path)
        if not history or not description:
            return []

        scored: List[Tuple[HistoricalTask, float]] = []
        for entry in history:
            task = _dict_to_historical_task(entry)
            sim = _jaccard_similarity(description, task.description)
            if sim >= min_similarity:
                scored.append((task, sim))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:max_results]

    def get_real_model_prices(self) -> Dict[str, Dict[str, float]]:
        """Calculate REAL model prices from actual cost events.

        Instead of hardcoded prices, compute from historical data:
        price_per_input_token = sum(cost) / sum(input_tokens)

        Falls back to hardcoded prices ONLY if no historical data exists.
        When falling back, marks the source as "default" not "measured".

        Returns: {model: {input: price, output: price, source: "measured"|"default"}}
        """
        events = _load_jsonl(self.cost_events_path)

        # Aggregate tokens and costs per model
        model_data: Dict[str, Dict[str, float]] = {}
        for ev in events:
            model = ev.get("model", "")
            if not model:
                continue
            if model not in model_data:
                model_data[model] = {
                    "total_cost": 0.0,
                    "total_in": 0,
                    "total_out": 0,
                }
            model_data[model]["total_cost"] += float(ev.get("estimated_cost_usd", 0.0))
            model_data[model]["total_in"] += int(ev.get("input_tokens", 0))
            model_data[model]["total_out"] += int(ev.get("output_tokens", 0))

        result: Dict[str, Dict[str, float]] = {}

        # Calculate measured prices
        for model, data in model_data.items():
            total_tokens = data["total_in"] + data["total_out"]
            if total_tokens > 0 and data["total_cost"] > 0:
                # Approximate split: use default ratio to apportion cost
                defaults = DEFAULT_MODEL_PRICES.get(model, {"input": 3.0, "output": 15.0})
                default_in_rate = defaults.get("input", 3.0)
                default_out_rate = defaults.get("output", 15.0)

                # Estimate what fraction of cost is input vs output using default ratios
                est_in_cost = data["total_in"] * default_in_rate / 1_000_000
                est_out_cost = data["total_out"] * default_out_rate / 1_000_000
                est_total = est_in_cost + est_out_cost

                if est_total > 0:
                    # Scale to match actual total cost
                    scale = data["total_cost"] / est_total
                    measured_in = default_in_rate * scale
                    measured_out = default_out_rate * scale
                else:
                    measured_in = default_in_rate
                    measured_out = default_out_rate

                result[model] = {
                    "input": round(measured_in, 4),
                    "output": round(measured_out, 4),
                    "source": "measured",
                }
            else:
                # No data for this model -- use defaults
                defaults = DEFAULT_MODEL_PRICES.get(model, {"input": 3.0, "output": 15.0})
                result[model] = {
                    "input": defaults.get("input", 3.0),
                    "output": defaults.get("output", 15.0),
                    "source": "default",
                }

        # Add default entries for models not seen in cost events
        for model, prices in DEFAULT_MODEL_PRICES.items():
            if model not in result:
                result[model] = {
                    "input": prices["input"],
                    "output": prices["output"],
                    "source": "default",
                }

        return result

    def estimate_per_phase(
        self,
        task_type: str = "feature",
        model_override: Optional[str] = None,
    ) -> Dict[str, float]:
        """Estimate cost per SDD phase based on historical averages.

        Returns: {explore: $0.10, propose: $0.50, spec: $0.15, ...}
        Uses real historical data when available.
        """
        history = _load_jsonl(self.history_path)

        # Try to compute from history
        phase_costs: Dict[str, List[float]] = {p: [] for p in SDD_PHASES}
        phase_counts: Dict[str, int] = {p: 0 for p in SDD_PHASES}

        for entry in history:
            if entry.get("task_type") != task_type and history:
                # Still include as general data if not many matches
                pass
            total_cost = float(entry.get("total_cost_usd", 0))
            phases = entry.get("phases_executed", [])
            if phases and total_cost > 0:
                # Distribute cost evenly across phases (rough approximation)
                per_phase = total_cost / len(phases)
                for phase in phases:
                    if phase in phase_costs:
                        phase_costs[phase].append(per_phase)
                        phase_counts[phase] += 1

        # If we have historical data, use averages
        has_data = any(len(v) > 0 for v in phase_costs.values())
        if has_data:
            result = {}
            for phase in SDD_PHASES:
                if phase_costs[phase]:
                    import statistics
                    result[phase] = round(statistics.mean(phase_costs[phase]), 2)
                else:
                    result[phase] = self._default_phase_cost(phase, model_override)
            return result

        # Fall back to model-routing based estimates
        return {
            phase: self._default_phase_cost(phase, model_override)
            for phase in SDD_PHASES
        }

    def get_cost_trends(self, days: int = 30) -> Dict:
        """Cost trends over time.

        Returns: {daily_avg, weekly_avg, trend_direction,
                  cheapest_day, most_expensive_day,
                  cost_per_task_trend}
        """
        events = _load_jsonl(self.cost_events_path)
        if not events:
            return {
                "daily_avg": 0.0,
                "weekly_avg": 0.0,
                "trend_direction": "stable",
                "cheapest_day": None,
                "most_expensive_day": None,
                "cost_per_task_trend": "stable",
            }

        now = datetime.now(timezone.utc)
        cutoff_seconds = days * 86400

        # Group by day
        daily: Dict[str, float] = {}
        for ev in events:
            ts = _parse_timestamp(ev.get("timestamp", ""))
            if not ts:
                continue
            age = (now - ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else now - ts).total_seconds()
            if age > cutoff_seconds:
                continue
            day_key = ts.strftime("%Y-%m-%d")
            cost = float(ev.get("estimated_cost_usd", 0))
            daily[day_key] = daily.get(day_key, 0.0) + cost

        if not daily:
            return {
                "daily_avg": 0.0,
                "weekly_avg": 0.0,
                "trend_direction": "stable",
                "cheapest_day": None,
                "most_expensive_day": None,
                "cost_per_task_trend": "stable",
            }

        values = list(daily.values())
        daily_avg = sum(values) / len(values)
        weekly_avg = daily_avg * 7

        # Trend: compare first half vs second half
        sorted_days = sorted(daily.items())
        mid = len(sorted_days) // 2
        if mid > 0:
            first_half_avg = sum(v for _, v in sorted_days[:mid]) / mid
            second_half_avg = sum(v for _, v in sorted_days[mid:]) / max(1, len(sorted_days) - mid)
            if second_half_avg > first_half_avg * 1.15:
                trend = "up"
            elif second_half_avg < first_half_avg * 0.85:
                trend = "down"
            else:
                trend = "stable"
        else:
            trend = "stable"

        cheapest = min(daily, key=daily.get)  # type: ignore[arg-type]
        most_expensive = max(daily, key=daily.get)  # type: ignore[arg-type]

        return {
            "daily_avg": round(daily_avg, 2),
            "weekly_avg": round(weekly_avg, 2),
            "trend_direction": trend,
            "cheapest_day": cheapest,
            "most_expensive_day": most_expensive,
            "cost_per_task_trend": trend,
        }

    def format_prediction(self, prediction: CostPrediction) -> str:
        """Format prediction for display."""
        confidence_label = "VERY LOW"
        if prediction.confidence >= 0.8:
            confidence_label = "HIGH"
        elif prediction.confidence >= 0.5:
            confidence_label = "MEDIUM"
        elif prediction.confidence >= 0.3:
            confidence_label = "LOW"

        lines = [
            "Cost Prediction",
            f"  Estimated: ${prediction.estimated_cost_min:.2f} -- "
            f"${prediction.estimated_cost_max:.2f} "
            f"(mid: ${prediction.estimated_cost_mid:.2f})",
            f"  Confidence: {confidence_label} ({prediction.confidence:.2f})",
            f"  Based on: {prediction.basis}",
        ]

        if prediction.similar_tasks:
            lines.append(f"  Similar tasks ({len(prediction.similar_tasks)}):")
            for st in prediction.similar_tasks[:5]:
                desc = st.get("description", "")[:50]
                cost = st.get("cost", 0)
                sim = st.get("similarity", 0)
                lines.append(f"    - \"{desc}\" -- ${cost:.2f} (similarity: {sim:.2f})")

        if prediction.calibration_applied != 1.0:
            lines.append(f"  Calibration: x{prediction.calibration_applied:.2f}")

        if prediction.breakdown:
            lines.append("  Phase breakdown:")
            for phase, cost in prediction.breakdown.items():
                model = PHASE_MODEL_DEFAULTS.get(phase, "sonnet")
                lines.append(f"    {phase}: ${cost:.2f} ({model})")

        if prediction.recommendation:
            lines.append(f"  Recommendation: {prediction.recommendation}")

        return "\n".join(lines)

    def format_price_table(self) -> str:
        """Show current model prices (measured vs default)."""
        prices = self.get_real_model_prices()

        # Filter to unique entries (skip aliases)
        seen_prices: Dict[str, bool] = {}
        unique: List[Tuple[str, Dict]] = []
        for model, data in sorted(prices.items()):
            key = f"{data['input']:.4f}_{data['output']:.4f}_{data['source']}"
            if key not in seen_prices or len(model) < 10:
                seen_prices[key] = True
                unique.append((model, data))

        lines = [
            "Model Prices:",
            f"{'Model':<25} {'Input/1M':>10} {'Output/1M':>12} {'Source':>10}",
            "-" * 60,
        ]

        for model, data in unique:
            lines.append(
                f"{model:<25} ${data['input']:>8.2f} ${data['output']:>10.2f} "
                f"{data['source']:>10}"
            )

        lines.append("-" * 60)
        lines.append("Note: 'measured' = calculated from real API responses.")
        lines.append("      'default' = no usage data, using published prices.")

        return "\n".join(lines)

    # -------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------

    def _predict_from_model_routing(self, task_type: str) -> CostPrediction:
        """Fall back to model-routing based estimate when no history exists."""
        breakdown = self.estimate_per_phase(task_type)
        total = sum(breakdown.values())

        return CostPrediction(
            estimated_cost_min=round(total * 0.7, 2),
            estimated_cost_max=round(total * 1.5, 2),
            estimated_cost_mid=round(total, 2),
            confidence=0.15,
            basis="no_data" if total == 0 else "model_routing",
            similar_tasks=[],
            calibration_applied=1.0,
            breakdown=breakdown,
            recommendation="No historical data. Estimate based on default model routing.",
        )

    def _get_calibration_factor(self) -> float:
        """Get calibration multiplier from estimation_calibrator if available."""
        try:
            from lib.estimation_calibrator import get_calibration_factor
            factors = get_calibration_factor("orchestrator")
            if factors.get("sample_size", 0) >= 10:
                return factors.get("effort_bias", 1.0)
        except (ImportError, Exception):
            pass
        return 1.0

    def _calculate_confidence(
        self, similar: List[Tuple[HistoricalTask, float]]
    ) -> float:
        """Calculate confidence level based on similar task count and similarity."""
        if not similar:
            return 0.15

        count = len(similar)
        max_sim = max(sim for _, sim in similar)

        if count >= 5 and max_sim >= 0.7:
            return min(0.9, 0.8 + (max_sim - 0.7) * 0.33)
        elif count >= 2:
            return min(0.7, 0.5 + (count - 2) * 0.05 + (max_sim - 0.5) * 0.2)
        else:
            return min(0.5, 0.3 + (max_sim - 0.5) * 0.4)

    def _default_phase_cost(
        self, phase: str, model_override: Optional[str] = None
    ) -> float:
        """Estimate cost for a single phase using default model routing."""
        model = model_override or PHASE_MODEL_DEFAULTS.get(phase, "sonnet")
        prices = DEFAULT_MODEL_PRICES.get(model, DEFAULT_MODEL_PRICES.get("sonnet", {}))

        # Default token estimates per phase
        phase_tokens: Dict[str, Tuple[int, int]] = {
            "explore": (5000, 2000),
            "propose": (8000, 5000),
            "spec": (6000, 4000),
            "design": (10000, 6000),
            "tasks": (5000, 3000),
            "apply": (15000, 8000),
            "verify": (8000, 4000),
            "archive": (3000, 1500),
        }

        tokens_in, tokens_out = phase_tokens.get(phase, (5000, 3000))
        cost = (
            tokens_in * prices.get("input", 3.0) / 1_000_000
            + tokens_out * prices.get("output", 15.0) / 1_000_000
        )
        return round(cost, 2)

    def _generate_recommendation(
        self, breakdown: Dict[str, float], total_cost: float
    ) -> str:
        """Generate a cost optimization recommendation."""
        if not breakdown:
            return ""

        # Find the most expensive phase
        if breakdown:
            most_expensive = max(breakdown, key=breakdown.get)  # type: ignore[arg-type]
            model = PHASE_MODEL_DEFAULTS.get(most_expensive, "sonnet")
            if model == "opus":
                return (
                    f"Most expensive phase: {most_expensive} (opus). "
                    f"Consider sonnet for non-reasoning phases."
                )

        if total_cost > 2.0:
            return "High estimated cost. Consider splitting into smaller tasks."
        elif total_cost < 0.5:
            return "Low cost estimate. Good candidate for full SDD pipeline."

        return "Use sonnet for all phases except design and propose."
