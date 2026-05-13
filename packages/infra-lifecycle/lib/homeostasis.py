# SCOPE: both
# scope: both
"""Homeostasis — Continuous Self-Regulation for Cognitive OS.

Like biological homeostasis (temperature, pH, blood sugar), this module
monitors the organism's health metrics and adjusts internal parameters
to maintain optimal operating conditions.

Control loops:
    1. Token efficiency -> capability level adjustment
    2. Error rate -> safety net adjustment
    3. Cost -> model routing adjustment
    4. Task success -> self-improvement trigger
    5. Overhead ratio -> symbiosis alert

Usage:
    from lib.homeostasis import Homeostasis

    h = Homeostasis("/path/to/project")
    metrics = h.collect_metrics()
    adjustments = h.diagnose(metrics)
    applied = h.apply_safe_adjustments(adjustments)
    report = h.format_health_report(metrics, adjustments)

Python 3.9+ compatible.
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class HealthMetrics:
    """Current organism health snapshot."""

    tokens_per_session_avg: float  # Average tokens consumed per session (last 5)
    error_rate_24h: float  # Errors per total tasks in last 24h (0.0-1.0)
    cost_today_usd: float  # Total cost today
    budget_remaining_pct: float  # % of daily budget remaining (0.0-1.0)
    task_success_rate: float  # Successful tasks / total tasks (0.0-1.0)
    overhead_ratio: float  # Overhead tokens / useful tokens (0.0-1.0)
    current_capability_level: int  # Current level (1-5)
    current_phase: str  # reconstruction/stabilization/production/maintenance


@dataclass
class Adjustment:
    """A homeostatic adjustment recommendation."""

    system: str  # capability_level | model_routing | self_improvement | symbiosis
    action: str  # raise | lower | downgrade | trigger | alert
    reason: str  # Why this adjustment
    current_value: str  # Current state
    recommended_value: str  # Recommended state
    auto_apply: bool  # Can be auto-applied (safe) or requires human approval


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LEVEL_NAMES: Dict[int, str] = {
    1: "basic",
    2: "good",
    3: "excellent",
    4: "autonomous",
    5: "autonomous+",
}

_24H_SECONDS = 86400


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path, max_age_seconds: Optional[int] = None) -> List[dict]:
    """Read a JSONL file, optionally filtering by age.

    Returns an empty list if the file does not exist or cannot be parsed.
    Lines that fail JSON parsing are silently skipped.
    """
    if not path.is_file():
        return []

    now_epoch = time.time()
    entries: List[dict] = []

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue

                if max_age_seconds is not None:
                    ts_epoch = obj.get("timestamp_epoch")
                    if ts_epoch is None:
                        # Try ISO timestamp as fallback
                        ts_str = obj.get("timestamp", "")
                        if ts_str:
                            try:
                                from datetime import datetime

                                dt = datetime.fromisoformat(
                                    ts_str.replace("Z", "+00:00")
                                )
                                ts_epoch = dt.timestamp()
                            except (ValueError, TypeError):
                                ts_epoch = None

                    if ts_epoch is not None:
                        try:
                            if now_epoch - float(ts_epoch) > max_age_seconds:
                                continue
                        except (TypeError, ValueError):
                            pass

                entries.append(obj)
    except OSError:
        return []

    return entries


def _parse_config(config_path: Path) -> dict:
    """Parse cognitive-os.yaml with fallback for missing PyYAML."""
    if not config_path.is_file():
        return {}

    text = config_path.read_text(encoding="utf-8", errors="replace")

    if yaml is not None:
        try:
            return yaml.safe_load(text) or {}
        except Exception:
            return {}

    # Minimal fallback: extract key values we need
    result: dict = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("phase:"):
            val = stripped.split(":", 1)[1].strip().split("#")[0].strip()
            result.setdefault("project", {})["phase"] = val
        if stripped.startswith("level:"):
            val = stripped.split(":", 1)[1].strip().split("#")[0].strip()
            try:
                result.setdefault("model_capability", {})["level"] = int(val)
            except ValueError:
                pass
        if stripped.startswith("daily_alert_usd:"):
            val = stripped.split(":", 1)[1].strip().split("#")[0].strip()
            try:
                result.setdefault("resources", {}).setdefault("budget", {})[
                    "daily_alert_usd"
                ] = float(val)
            except ValueError:
                pass
    return result


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class Homeostasis:
    """Monitors organism health and recommends/applies adjustments.

    The control loop runs at session end (via session-cleanup.sh)
    or on-demand via the Singularity controller.
    """

    def __init__(self, project_dir: str) -> None:
        self.project_dir = Path(project_dir)
        self.config_path = self.project_dir / "cognitive-os.yaml"
        self.metrics_dir = self.project_dir / ".cognitive-os" / "metrics"

        # Biological "set points" — thresholds that define homeostatic balance
        self.thresholds: Dict[str, float] = {
            "token_efficiency_high": 50000,  # tokens/session above = too expensive
            "token_efficiency_low": 5000,  # tokens/session below = maybe too restricted
            "error_rate_high": 0.20,  # >20% error rate = organism is sick
            "error_rate_low": 0.05,  # <5% error rate = healthy
            "cost_budget_warn": 0.80,  # >80% budget used = metabolic stress
            "cost_budget_critical": 0.95,  # >95% = starvation
            "task_success_low": 0.70,  # <70% success = organism failing
            "overhead_ratio_parasitic": 0.30,  # >30% overhead = parasitic
            "overhead_ratio_healthy": 0.10,  # <10% = healthy symbiosis
        }

    # ------------------------------------------------------------------
    # Metrics collection
    # ------------------------------------------------------------------

    def _read_config(self) -> dict:
        """Read and parse the cognitive-os.yaml configuration."""
        return _parse_config(self.config_path)

    def _get_daily_budget(self, config: dict) -> float:
        """Extract the daily budget from config, with a safe default."""
        try:
            return float(
                config.get("resources", {})
                .get("budget", {})
                .get("daily_alert_usd", 10.0)
            )
        except (TypeError, ValueError):
            return 10.0

    def _get_capability_level(self, config: dict) -> int:
        """Extract current capability level from config."""
        try:
            level = int(config.get("model_capability", {}).get("level", 3))
        except (TypeError, ValueError):
            return 3
        return max(1, min(5, level))

    def _get_phase(self, config: dict) -> str:
        """Extract current project phase from config."""
        phase = config.get("project", {}).get("phase", "reconstruction")
        if phase not in ("reconstruction", "stabilization", "production", "maintenance"):
            return "reconstruction"
        return phase

    def _collect_cost_today(self) -> float:
        """Sum cost from cost-events.jsonl for today (last 24h)."""
        path = self.metrics_dir / "cost-events.jsonl"
        entries = _read_jsonl(path, max_age_seconds=_24H_SECONDS)
        total = 0.0
        for entry in entries:
            try:
                total += float(entry.get("estimated_cost_usd", 0))
            except (TypeError, ValueError):
                pass
        return round(total, 4)

    def _collect_error_rate(self) -> Tuple[int, int]:
        """Return (error_count_24h, total_tasks_24h) from metrics files."""
        error_path = self.metrics_dir / "error-learning.jsonl"
        errors_24h = _read_jsonl(error_path, max_age_seconds=_24H_SECONDS)
        error_count = len(errors_24h)

        skill_path = self.metrics_dir / "skill-metrics.jsonl"
        tasks_24h = _read_jsonl(skill_path, max_age_seconds=_24H_SECONDS)
        total_tasks = len(tasks_24h)

        return error_count, max(total_tasks, 1)

    def _collect_task_success_rate(self) -> float:
        """Calculate task success rate from skill-metrics.jsonl (last 24h)."""
        path = self.metrics_dir / "skill-metrics.jsonl"
        entries = _read_jsonl(path, max_age_seconds=_24H_SECONDS)
        if not entries:
            return 1.0  # No data = assume healthy

        successes = sum(
            1 for e in entries if e.get("success") is True
        )
        return round(successes / len(entries), 4)

    def _collect_tokens_per_session(self) -> float:
        """Estimate average tokens per session from recent cost events.

        Uses cost-events.jsonl, grouping by rough session boundaries.
        Falls back to a simple per-entry average if session grouping is unclear.
        """
        path = self.metrics_dir / "cost-events.jsonl"
        entries = _read_jsonl(path, max_age_seconds=_24H_SECONDS * 7)  # last 7 days
        if not entries:
            return 0.0

        total_tokens = 0
        for entry in entries:
            try:
                total_tokens += int(entry.get("input_tokens", 0))
                total_tokens += int(entry.get("output_tokens", 0))
            except (TypeError, ValueError):
                pass

        # Rough estimate: assume ~5 sessions in the data window
        # Better heuristic: count distinct "session" values if present
        sessions_seen: set = set()
        for entry in entries:
            sid = entry.get("session_id") or entry.get("session")
            if sid:
                sessions_seen.add(sid)

        num_sessions = len(sessions_seen) if sessions_seen else max(len(entries) // 10, 1)
        return round(total_tokens / max(num_sessions, 1), 1)

    def _collect_overhead_ratio(self) -> float:
        """Estimate governance overhead ratio from performance metrics.

        Reads performance.jsonl and calculates what fraction of total duration
        was spent on hooks/gates vs. actual work.
        Falls back to a healthy default if no data.
        """
        path = self.metrics_dir / "performance.jsonl"
        entries = _read_jsonl(path, max_age_seconds=_24H_SECONDS)
        if not entries:
            return 0.0  # No data = assume no overhead

        overhead_ms = 0.0
        total_ms = 0.0
        for entry in entries:
            try:
                duration = float(entry.get("duration_ms", 0))
            except (TypeError, ValueError):
                continue

            total_ms += duration
            component = entry.get("component", "")
            # Hooks, gates, validators are overhead
            if any(
                prefix in component
                for prefix in ("hook:", "gate:", "validator:", "safety:")
            ):
                overhead_ms += duration

        if total_ms <= 0:
            return 0.0

        return round(overhead_ms / total_ms, 4)

    def collect_metrics(self) -> HealthMetrics:
        """Gather current health metrics from JSONL files and config."""
        config = self._read_config()

        cost_today = self._collect_cost_today()
        daily_budget = self._get_daily_budget(config)
        budget_remaining_pct = max(0.0, 1.0 - (cost_today / daily_budget)) if daily_budget > 0 else 0.0

        error_count, total_tasks = self._collect_error_rate()
        error_rate = error_count / total_tasks if total_tasks > 0 else 0.0

        return HealthMetrics(
            tokens_per_session_avg=self._collect_tokens_per_session(),
            error_rate_24h=round(error_rate, 4),
            cost_today_usd=cost_today,
            budget_remaining_pct=round(budget_remaining_pct, 4),
            task_success_rate=self._collect_task_success_rate(),
            overhead_ratio=self._collect_overhead_ratio(),
            current_capability_level=self._get_capability_level(config),
            current_phase=self._get_phase(config),
        )

    # ------------------------------------------------------------------
    # Diagnosis
    # ------------------------------------------------------------------

    def diagnose(self, metrics: HealthMetrics) -> List[Adjustment]:
        """Compare metrics against thresholds and recommend adjustments.

        Like a doctor examining vital signs.
        """
        adjustments: List[Adjustment] = []

        # Control loop 1: Token efficiency -> capability level
        if metrics.tokens_per_session_avg > self.thresholds["token_efficiency_high"]:
            if metrics.current_capability_level < 5:
                adjustments.append(
                    Adjustment(
                        system="capability_level",
                        action="raise",
                        reason=(
                            f"Token consumption too high "
                            f"({metrics.tokens_per_session_avg:,.0f} tokens/session avg). "
                            "Raising capability level will disable unnecessary safety hooks."
                        ),
                        current_value=str(metrics.current_capability_level),
                        recommended_value=str(
                            min(metrics.current_capability_level + 1, 5)
                        ),
                        auto_apply=False,  # Capability level changes need human approval
                    )
                )

        # Control loop 2: Error rate -> safety nets
        if metrics.error_rate_24h > self.thresholds["error_rate_high"]:
            if metrics.current_capability_level > 1:
                adjustments.append(
                    Adjustment(
                        system="capability_level",
                        action="lower",
                        reason=(
                            f"Error rate too high ({metrics.error_rate_24h:.0%}). "
                            "Lowering capability level will activate more safety hooks."
                        ),
                        current_value=str(metrics.current_capability_level),
                        recommended_value=str(
                            max(metrics.current_capability_level - 1, 1)
                        ),
                        auto_apply=False,
                    )
                )

        # Control loop 3: Cost -> model routing
        budget_used_pct = 1.0 - metrics.budget_remaining_pct
        if budget_used_pct >= self.thresholds["cost_budget_critical"]:
            adjustments.append(
                Adjustment(
                    system="model_routing",
                    action="downgrade",
                    reason=(
                        f"Budget nearly exhausted ({budget_used_pct:.0%} used). "
                        "Downgrade to cheaper models."
                    ),
                    current_value="current routing table",
                    recommended_value="force haiku for non-critical tasks",
                    auto_apply=True,  # Budget protection is auto-safe
                )
            )
        elif budget_used_pct >= self.thresholds["cost_budget_warn"]:
            adjustments.append(
                Adjustment(
                    system="model_routing",
                    action="downgrade",
                    reason=(
                        f"Budget pressure ({budget_used_pct:.0%} used). "
                        "Consider downgrading opus to sonnet."
                    ),
                    current_value="current routing table",
                    recommended_value="force sonnet for non-critical tasks",
                    auto_apply=True,
                )
            )

        # Control loop 4: Task success -> self-improvement
        if metrics.task_success_rate < self.thresholds["task_success_low"]:
            adjustments.append(
                Adjustment(
                    system="self_improvement",
                    action="trigger",
                    reason=(
                        f"Task success rate below threshold "
                        f"({metrics.task_success_rate:.0%} < 70%). "
                        "Self-improvement needed."
                    ),
                    current_value=f"{metrics.task_success_rate:.0%}",
                    recommended_value="run /self-improve",
                    auto_apply=False,  # Self-improvement changes rules/skills
                )
            )

        # Control loop 5: Overhead ratio -> symbiosis
        if metrics.overhead_ratio > self.thresholds["overhead_ratio_parasitic"]:
            adjustments.append(
                Adjustment(
                    system="symbiosis",
                    action="alert",
                    reason=(
                        f"Overhead ratio is parasitic "
                        f"({metrics.overhead_ratio:.0%} of tokens are governance overhead). "
                        "The organism is consuming more than it's providing."
                    ),
                    current_value=f"{metrics.overhead_ratio:.0%}",
                    recommended_value=(
                        f"target <{self.thresholds['overhead_ratio_healthy']:.0%}"
                    ),
                    auto_apply=False,
                )
            )

        return adjustments

    # ------------------------------------------------------------------
    # Safe auto-apply
    # ------------------------------------------------------------------

    def apply_safe_adjustments(self, adjustments: List[Adjustment]) -> List[str]:
        """Apply adjustments that are safe to auto-apply.

        Currently, only model routing downgrades are auto-safe.
        Returns list of human-readable strings describing applied actions.
        """
        applied: List[str] = []
        for adj in adjustments:
            if not adj.auto_apply:
                continue

            if adj.system == "model_routing" and adj.action == "downgrade":
                # Write a flag file that model_router.py can read at next invocation
                flag_path = self.metrics_dir / "model-downgrade-active.json"
                try:
                    self.metrics_dir.mkdir(parents=True, exist_ok=True)
                    flag_data = {
                        "timestamp": _iso_now(),
                        "reason": adj.reason,
                        "recommended": adj.recommended_value,
                    }
                    flag_path.write_text(
                        json.dumps(flag_data, indent=2), encoding="utf-8"
                    )
                except OSError:
                    pass  # Best-effort; never crash

            applied.append(
                f"AUTO-APPLIED: {adj.system}/{adj.action} -- {adj.reason}"
            )

        return applied

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def format_health_report(
        self, metrics: HealthMetrics, adjustments: List[Adjustment]
    ) -> str:
        """Format a human-readable health report."""
        lines: List[str] = []
        lines.append("HOMEOSTASIS REPORT")
        lines.append("\u2550" * 40)  # ═

        # Tokens/session
        tok_status = self._status_indicator(
            metrics.tokens_per_session_avg,
            self.thresholds["token_efficiency_high"],
            higher_is_worse=True,
        )
        lines.append(
            f"Tokens/session: {metrics.tokens_per_session_avg:,.0f} "
            f"({tok_status} -- threshold: "
            f"{self.thresholds['token_efficiency_high']:,.0f})"
        )

        # Error rate
        err_status = self._status_indicator(
            metrics.error_rate_24h,
            self.thresholds["error_rate_high"],
            higher_is_worse=True,
        )
        lines.append(
            f"Error rate (24h): {metrics.error_rate_24h:.0%} "
            f"({err_status} -- threshold: "
            f"{self.thresholds['error_rate_high']:.0%})"
        )

        # Budget
        daily_budget = self._get_daily_budget(self._read_config())
        lines.append(
            f"Budget used today: {(1 - metrics.budget_remaining_pct):.0%} "
            f"(${metrics.cost_today_usd:.2f} of ${daily_budget:.2f})"
        )

        # Task success
        success_status = self._status_indicator(
            metrics.task_success_rate,
            self.thresholds["task_success_low"],
            higher_is_worse=False,
        )
        lines.append(
            f"Task success rate: {metrics.task_success_rate:.0%} "
            f"({success_status} -- threshold: "
            f"{self.thresholds['task_success_low']:.0%})"
        )

        # Overhead
        overhead_status = self._status_indicator(
            metrics.overhead_ratio,
            self.thresholds["overhead_ratio_parasitic"],
            higher_is_worse=True,
        )
        lines.append(
            f"Overhead ratio: {metrics.overhead_ratio:.0%} "
            f"({overhead_status} -- threshold: "
            f"{self.thresholds['overhead_ratio_parasitic']:.0%})"
        )

        # Context
        level_name = _LEVEL_NAMES.get(metrics.current_capability_level, "unknown")
        lines.append(f"Capability level: {metrics.current_capability_level} ({level_name})")
        lines.append(f"Phase: {metrics.current_phase}")

        # Adjustments section
        lines.append("")
        if not adjustments:
            lines.append("ADJUSTMENTS: None needed. Organism is healthy.")
        else:
            lines.append(f"ADJUSTMENTS: {len(adjustments)} recommended")
            lines.append("-" * 40)
            for i, adj in enumerate(adjustments, 1):
                auto_tag = "[AUTO]" if adj.auto_apply else "[MANUAL]"
                lines.append(
                    f"  {i}. {auto_tag} {adj.system}/{adj.action}: {adj.reason}"
                )
                lines.append(
                    f"     Current: {adj.current_value} -> "
                    f"Recommended: {adj.recommended_value}"
                )

        return "\n".join(lines)

    @staticmethod
    def _status_indicator(value: float, threshold: float, higher_is_worse: bool) -> str:
        """Return a text status indicator based on value vs threshold.

        Uses text markers instead of emoji for compatibility with agent rules.
        """
        if higher_is_worse:
            if value >= threshold:
                return "!! CRITICAL"
            elif value >= threshold * 0.75:
                return ">> HIGH"
            else:
                return "-- HEALTHY"
        else:
            if value <= threshold:
                return "!! CRITICAL"
            elif value <= threshold * 1.25:
                return ">> LOW"
            else:
                return "-- HEALTHY"

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log_health_check(
        self, metrics: HealthMetrics, adjustments: List[Adjustment]
    ) -> None:
        """Log to metrics/homeostasis.jsonl."""
        log_path = self.metrics_dir / "homeostasis.jsonl"
        try:
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": _iso_now(),
                "tokens_per_session_avg": metrics.tokens_per_session_avg,
                "error_rate_24h": metrics.error_rate_24h,
                "cost_today_usd": metrics.cost_today_usd,
                "budget_remaining_pct": metrics.budget_remaining_pct,
                "task_success_rate": metrics.task_success_rate,
                "overhead_ratio": metrics.overhead_ratio,
                "capability_level": metrics.current_capability_level,
                "phase": metrics.current_phase,
                "adjustments_count": len(adjustments),
                "adjustments": [
                    {
                        "system": a.system,
                        "action": a.action,
                        "auto_apply": a.auto_apply,
                    }
                    for a in adjustments
                ],
            }
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, separators=(",", ":")) + "\n")
        except OSError:
            pass  # Best-effort; never crash on logging failure

    # ------------------------------------------------------------------
    # Convenience: full health check cycle
    # ------------------------------------------------------------------

    def run(self) -> Tuple[HealthMetrics, List[Adjustment], List[str]]:
        """Execute a full homeostasis cycle: collect, diagnose, apply, log.

        Returns:
            Tuple of (metrics, adjustments, applied_actions).
        """
        metrics = self.collect_metrics()
        adjustments = self.diagnose(metrics)
        applied = self.apply_safe_adjustments(adjustments)
        self.log_health_check(metrics, adjustments)
        return metrics, adjustments, applied


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _iso_now() -> str:
    """Return current UTC time in ISO 8601 format."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
