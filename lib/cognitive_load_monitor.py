# scope: both
"""Cognitive Load Monitor -- Detect agent degradation from context overload.

Tracks agent cognitive health across a session by measuring quality metrics
at each tool call and detecting degradation patterns. The AI equivalent
of "burnout" detection.

Based on research from the WISC framework (arxiv 2507.11538) which found
that >150 instructions degrade LLM performance. Cognitive OS loads ~88 rules
(~73K tokens), making degradation monitoring essential.

Degradation signals:
- context_saturation: output quality drops as context fills
- instruction_drift: agent stops following preamble instructions
- hallucination_spike: unverified claims increase over time
- tool_confusion: tool call success rate drops
- compound_degradation: 3+ signals simultaneously

Usage:
    from lib.cognitive_load_monitor import CognitiveLoadMonitor

    monitor = CognitiveLoadMonitor()
    snap = monitor.record_snapshot(
        tool_call_number=42,
        output_length=1500,
        task_complexity="medium",
        preamble_compliance=0.9,
        hallucination_count=0,
        instruction_following=0.95,
        tool_call_success=1.0,
    )
    report = monitor.format_health_report()

Python 3.9+ compatible. No external dependencies.
Author: luum
"""

import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Heuristic: average tokens consumed per tool call + response
_TOKENS_PER_TOOL_CALL_LOW = 500
_TOKENS_PER_TOOL_CALL_HIGH = 1000

# Default context window size for Claude Opus 4.6
_DEFAULT_CONTEXT_WINDOW = 1_000_000

# Number of initial snapshots used to establish baseline
_BASELINE_WINDOW = 5

# Number of recent snapshots used for current health assessment
_RECENT_WINDOW = 5

# Degradation thresholds
_OUTPUT_DROP_THRESHOLD = 0.30  # 30% drop from baseline triggers signal
_PREAMBLE_COMPLIANCE_MIN = 0.70  # below 70% triggers instruction_drift
_TOOL_SUCCESS_MIN = 0.80  # below 80% triggers tool_confusion
_HALLUCINATION_INCREASE_FACTOR = 3.0  # 3x baseline triggers spike
_COMPOUND_SIGNAL_MIN = 3  # 3+ signals = compound degradation
_SAVE_AND_SPLIT_THRESHOLD = 60.0  # health score below this recommends split

# Quality score weights (must sum to 1.0)
_WEIGHT_PREAMBLE = 0.25
_WEIGHT_INSTRUCTION = 0.25
_WEIGHT_TOOL_SUCCESS = 0.20
_WEIGHT_HALLUCINATION = 0.15
_WEIGHT_OUTPUT_PROPORTION = 0.15


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CognitiveSnapshot:
    """Point-in-time measurement of agent cognitive health."""

    timestamp: float
    tool_call_number: int  # sequential counter
    context_usage_pct: float  # estimated from tool call count

    # Quality metrics
    output_length: int  # chars in agent response
    task_complexity: str  # trivial/small/medium/large/critical
    preamble_compliance: float  # 0-1: did agent follow preamble instructions?
    hallucination_count: int  # claims not verified
    instruction_following: float  # 0-1: followed explicit instructions?
    tool_call_success: float  # 0-1: tools used correctly?

    # Degradation signals
    response_quality_score: float  # composite 0-100
    degradation_detected: bool
    degradation_type: Optional[str] = None
    # "context_saturation", "instruction_drift", "hallucination_spike",
    # "tool_confusion", "compound_degradation"


@dataclass
class DegradationSignal:
    """A single detected degradation signal."""

    signal_type: str
    severity: str  # "ok", "warn", "alert"
    detail: str
    value: float
    baseline_value: float


# ---------------------------------------------------------------------------
# Expected output length ranges by complexity (chars)
# ---------------------------------------------------------------------------

_EXPECTED_OUTPUT_RANGE: Dict[str, tuple] = {
    "trivial": (50, 500),
    "small": (200, 2000),
    "medium": (500, 5000),
    "large": (1000, 10000),
    "critical": (2000, 15000),
}


# ---------------------------------------------------------------------------
# Core monitor
# ---------------------------------------------------------------------------


class CognitiveLoadMonitor:
    """Tracks agent cognitive health across a session.

    Records snapshots at each significant tool call, establishes a quality
    baseline from the first N snapshots, then detects degradation trends.
    """

    def __init__(
        self,
        max_snapshots: int = 100,
        context_window: int = _DEFAULT_CONTEXT_WINDOW,
    ):
        self.snapshots: List[CognitiveSnapshot] = []
        self.max_snapshots = max_snapshots
        self.context_window = context_window
        self.baseline_quality: Optional[float] = None  # avg of first N
        self._baseline_output_length: Optional[float] = None
        self._baseline_hallucination_rate: Optional[float] = None

    # ----- recording -----

    def record_snapshot(
        self,
        tool_call_number: int,
        output_length: int,
        task_complexity: str = "medium",
        preamble_compliance: float = 1.0,
        hallucination_count: int = 0,
        instruction_following: float = 1.0,
        tool_call_success: float = 1.0,
        timestamp: Optional[float] = None,
    ) -> CognitiveSnapshot:
        """Record a cognitive health measurement and return the snapshot."""
        ts = timestamp if timestamp is not None else time.time()
        ctx_pct = self.estimate_context_usage(tool_call_number)

        quality = self._compute_quality_score(
            preamble_compliance=preamble_compliance,
            instruction_following=instruction_following,
            tool_call_success=tool_call_success,
            hallucination_count=hallucination_count,
            output_length=output_length,
            task_complexity=task_complexity,
        )

        snap = CognitiveSnapshot(
            timestamp=ts,
            tool_call_number=tool_call_number,
            context_usage_pct=ctx_pct,
            output_length=output_length,
            task_complexity=task_complexity,
            preamble_compliance=preamble_compliance,
            hallucination_count=hallucination_count,
            instruction_following=instruction_following,
            tool_call_success=tool_call_success,
            response_quality_score=quality,
            degradation_detected=False,
        )

        self.snapshots.append(snap)

        # Trim to max
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots :]

        # Establish baseline from first N snapshots
        if len(self.snapshots) == _BASELINE_WINDOW and self.baseline_quality is None:
            self._compute_baseline()

        # Check degradation
        deg = self.detect_degradation()
        if deg is not None:
            snap.degradation_detected = True
            snap.degradation_type = deg["type"]

        return snap

    # ----- degradation detection -----

    def detect_degradation(self) -> Optional[Dict[str, Any]]:
        """Analyze trend for degradation signals.

        Returns None if healthy, or dict with type, severity, recommendation,
        and individual signals.
        """
        if self.baseline_quality is None:
            return None  # not enough data

        signals = self._collect_signals()
        active = [s for s in signals if s.severity != "ok"]

        if not active:
            return None

        # Determine overall degradation type
        if len(active) >= _COMPOUND_SIGNAL_MIN:
            deg_type = "compound_degradation"
            severity = "alert"
        else:
            # Use the most severe signal
            alert_signals = [s for s in active if s.severity == "alert"]
            if alert_signals:
                deg_type = alert_signals[0].signal_type
                severity = "alert"
            else:
                deg_type = active[0].signal_type
                severity = "warn"

        recommendation = self._recommendation_for(deg_type, severity)

        return {
            "type": deg_type,
            "severity": severity,
            "signals": [
                {
                    "type": s.signal_type,
                    "severity": s.severity,
                    "detail": s.detail,
                    "value": s.value,
                    "baseline": s.baseline_value,
                }
                for s in active
            ],
            "recommendation": recommendation,
        }

    # ----- health score -----

    def cognitive_health_score(self) -> float:
        """Overall health 0-100. Based on last N snapshots vs baseline.

        Returns 100.0 if no data, baseline quality if < RECENT_WINDOW snapshots.
        """
        if not self.snapshots:
            return 100.0

        recent = self.snapshots[-_RECENT_WINDOW:]
        avg = sum(s.response_quality_score for s in recent) / len(recent)
        return round(avg, 1)

    # ----- context estimation -----

    def estimate_context_usage(self, tool_call_count: int) -> float:
        """Estimate context usage percentage from tool call count.

        Heuristic: ~500-1000 tokens per tool call + response.
        Uses the midpoint (750) for estimation.
        """
        avg_tokens = (_TOKENS_PER_TOOL_CALL_LOW + _TOKENS_PER_TOOL_CALL_HIGH) / 2
        estimated_tokens = tool_call_count * avg_tokens
        pct = (estimated_tokens / self.context_window) * 100.0
        return min(round(pct, 1), 100.0)

    # ----- reporting -----

    def format_health_report(self) -> str:
        """Human-readable cognitive health report."""
        health = self.cognitive_health_score()
        status = _health_status(health)

        lines = [
            f"Cognitive Health: {health}/100 ({status})",
            "",
        ]

        if self.baseline_quality is not None:
            recent = self.snapshots[-_RECENT_WINDOW:]
            recent_avg = sum(s.response_quality_score for s in recent) / len(recent)
            delta = recent_avg - self.baseline_quality
            delta_pct = (
                (delta / self.baseline_quality * 100)
                if self.baseline_quality > 0
                else 0
            )
            lines.append(
                f"Baseline (first {_BASELINE_WINDOW} calls): "
                f"{round(self.baseline_quality, 1)}/100"
            )
            lines.append(
                f"Current (last {min(len(recent), _RECENT_WINDOW)} calls): "
                f"{round(recent_avg, 1)}/100"
            )
            lines.append(
                f"Trend: {'+' if delta >= 0 else ''}{round(delta, 1)} points "
                f"({'+' if delta_pct >= 0 else ''}{round(delta_pct, 0)}%)"
            )
            lines.append("")

        # Signal details
        signals = self._collect_signals()
        lines.append("Signals:")
        for sig in signals:
            tag = "[OK]" if sig.severity == "ok" else f"[{sig.severity.upper()}]"
            lines.append(f"  {tag} {sig.detail}")

        # Context usage
        if self.snapshots:
            last = self.snapshots[-1]
            lines.append("")
            lines.append(f"Context usage: ~{last.context_usage_pct}%")

        # Recommendation
        deg = self.detect_degradation()
        if deg is not None:
            lines.append("")
            lines.append(f"Recommendation: {deg['recommendation']}")

        return "\n".join(lines)

    # ----- session split check -----

    def should_save_and_split(self) -> bool:
        """Returns True when degradation is severe enough to recommend
        saving state and splitting the session."""
        return self.cognitive_health_score() < _SAVE_AND_SPLIT_THRESHOLD

    # ----- persistence -----

    def save_metrics(
        self, path: str = ".cognitive-os/metrics/cognitive-load.jsonl"
    ) -> None:
        """Persist all snapshots to a JSONL metrics file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        with p.open("a") as f:
            for snap in self.snapshots:
                record = asdict(snap)
                f.write(json.dumps(record, default=str) + "\n")

    # ----- internal helpers -----

    def _compute_baseline(self) -> None:
        """Compute baseline metrics from first N snapshots."""
        window = self.snapshots[:_BASELINE_WINDOW]
        self.baseline_quality = sum(
            s.response_quality_score for s in window
        ) / len(window)
        self._baseline_output_length = sum(
            s.output_length for s in window
        ) / len(window)
        total_calls = len(window)
        total_hallucinations = sum(s.hallucination_count for s in window)
        self._baseline_hallucination_rate = (
            total_hallucinations / total_calls if total_calls > 0 else 0.0
        )

    def _compute_quality_score(
        self,
        preamble_compliance: float,
        instruction_following: float,
        tool_call_success: float,
        hallucination_count: int,
        output_length: int,
        task_complexity: str,
    ) -> float:
        """Compute composite quality score 0-100."""
        # Hallucination penalty: 0 hallucinations = 100, each one reduces by 20
        hallucination_score = max(0.0, 100.0 - hallucination_count * 20.0)

        # Output proportionality: check if output length is reasonable for complexity
        low, high = _EXPECTED_OUTPUT_RANGE.get(task_complexity, (200, 5000))
        if low <= output_length <= high:
            output_score = 100.0
        elif output_length < low:
            ratio = output_length / low if low > 0 else 0
            output_score = max(0.0, ratio * 100.0)
        else:
            # Over-verbose gets partial penalty
            ratio = high / output_length if output_length > 0 else 0
            output_score = max(50.0, ratio * 100.0)

        score = (
            preamble_compliance * 100.0 * _WEIGHT_PREAMBLE
            + instruction_following * 100.0 * _WEIGHT_INSTRUCTION
            + tool_call_success * 100.0 * _WEIGHT_TOOL_SUCCESS
            + hallucination_score * _WEIGHT_HALLUCINATION
            + output_score * _WEIGHT_OUTPUT_PROPORTION
        )
        return round(min(100.0, max(0.0, score)), 1)

    def _collect_signals(self) -> List[DegradationSignal]:
        """Collect all degradation signals from current state."""
        signals: List[DegradationSignal] = []

        if self.baseline_quality is None or len(self.snapshots) < _BASELINE_WINDOW:
            return signals

        recent = self.snapshots[-_RECENT_WINDOW:]

        # 1. Output length drop (context saturation)
        recent_avg_len = sum(s.output_length for s in recent) / len(recent)
        baseline_len = self._baseline_output_length or 1.0
        len_ratio = recent_avg_len / baseline_len if baseline_len > 0 else 1.0
        drop_pct = (1.0 - len_ratio) * 100.0
        if drop_pct > _OUTPUT_DROP_THRESHOLD * 100:
            signals.append(
                DegradationSignal(
                    signal_type="context_saturation",
                    severity="alert" if drop_pct > 50 else "warn",
                    detail=f"Output length: -{round(drop_pct)}% vs baseline",
                    value=recent_avg_len,
                    baseline_value=baseline_len,
                )
            )
        else:
            signals.append(
                DegradationSignal(
                    signal_type="context_saturation",
                    severity="ok",
                    detail=f"Output length: {'+' if drop_pct < 0 else '-'}{abs(round(drop_pct))}% vs baseline",
                    value=recent_avg_len,
                    baseline_value=baseline_len,
                )
            )

        # 2. Preamble compliance (instruction drift)
        recent_avg_preamble = sum(s.preamble_compliance for s in recent) / len(recent)
        if recent_avg_preamble < _PREAMBLE_COMPLIANCE_MIN:
            signals.append(
                DegradationSignal(
                    signal_type="instruction_drift",
                    severity="alert" if recent_avg_preamble < 0.5 else "warn",
                    detail=f"Preamble compliance: {round(recent_avg_preamble * 100)}%",
                    value=recent_avg_preamble,
                    baseline_value=1.0,
                )
            )
        else:
            signals.append(
                DegradationSignal(
                    signal_type="instruction_drift",
                    severity="ok",
                    detail=f"Preamble compliance: {round(recent_avg_preamble * 100)}%",
                    value=recent_avg_preamble,
                    baseline_value=1.0,
                )
            )

        # 3. Hallucination spike
        recent_hall_rate = sum(s.hallucination_count for s in recent) / len(recent)
        baseline_hall = self._baseline_hallucination_rate or 0.0
        threshold = max(baseline_hall * _HALLUCINATION_INCREASE_FACTOR, 1.0)
        if recent_hall_rate > threshold:
            signals.append(
                DegradationSignal(
                    signal_type="hallucination_spike",
                    severity="alert" if recent_hall_rate > threshold * 2 else "warn",
                    detail=(
                        f"Hallucination rate: {round(recent_hall_rate, 1)}/call "
                        f"(was {round(baseline_hall, 1)})"
                    ),
                    value=recent_hall_rate,
                    baseline_value=baseline_hall,
                )
            )
        else:
            signals.append(
                DegradationSignal(
                    signal_type="hallucination_spike",
                    severity="ok",
                    detail=f"Hallucination rate: {round(recent_hall_rate, 1)}/call",
                    value=recent_hall_rate,
                    baseline_value=baseline_hall,
                )
            )

        # 4. Tool call success (tool confusion)
        recent_avg_tool = sum(s.tool_call_success for s in recent) / len(recent)
        if recent_avg_tool < _TOOL_SUCCESS_MIN:
            signals.append(
                DegradationSignal(
                    signal_type="tool_confusion",
                    severity="alert" if recent_avg_tool < 0.6 else "warn",
                    detail=f"Tool success: {round(recent_avg_tool * 100)}%",
                    value=recent_avg_tool,
                    baseline_value=1.0,
                )
            )
        else:
            signals.append(
                DegradationSignal(
                    signal_type="tool_confusion",
                    severity="ok",
                    detail=f"Tool success: {round(recent_avg_tool * 100)}%",
                    value=recent_avg_tool,
                    baseline_value=1.0,
                )
            )

        return signals

    @staticmethod
    def _recommendation_for(deg_type: str, severity: str) -> str:
        """Generate recommendation based on degradation type."""
        recommendations = {
            "context_saturation": (
                "Save to Engram, reduce active rules, consider session split."
            ),
            "instruction_drift": (
                "Re-inject preamble instructions. "
                "Consider reducing loaded rules to essential set."
            ),
            "hallucination_spike": (
                "Enable cross-verification for remaining tasks. "
                "Validate all claims before accepting."
            ),
            "tool_confusion": (
                "Simplify remaining tasks. "
                "Reduce parallel tool calls. Consider session split."
            ),
            "compound_degradation": (
                "Multiple degradation signals detected. "
                "Save session state to Engram immediately. "
                "Split session before continuing."
            ),
        }
        base = recommendations.get(deg_type, "Review agent output quality manually.")
        if severity == "alert":
            return f"URGENT: {base}"
        return base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _health_status(score: float) -> str:
    """Human-readable status label for a health score."""
    if score >= 90:
        return "HEALTHY"
    elif score >= 75:
        return "GOOD"
    elif score >= 60:
        return "DEGRADING"
    elif score >= 40:
        return "DEGRADED"
    else:
        return "CRITICAL"
