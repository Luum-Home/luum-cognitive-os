# scope: both
"""Agent Planning Poker — Multi-agent complexity estimation with consensus.

Like human Planning Poker (Scrum), but 3 AI agents independently estimate
a task's complexity, then their estimates are compared and reconciled.

    Task -> Agent 1 (fast/cheap) estimates
         -> Agent 2 (deep/expensive) estimates
         -> Agent 3 (balanced) estimates
         -> Compare -> If divergent, explain -> Consensus

Complexity levels align with the Definition of Done rule:
TRIVIAL, SMALL, MEDIUM, LARGE, CRITICAL.
"""

import json
import os
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Complexity(Enum):
    """Task complexity levels aligned with definition-of-done.md."""

    TRIVIAL = 1
    SMALL = 2
    MEDIUM = 3
    LARGE = 4
    CRITICAL = 5


# Map string labels to Complexity enum for convenience.
_COMPLEXITY_MAP: Dict[str, Complexity] = {
    "trivial": Complexity.TRIVIAL,
    "small": Complexity.SMALL,
    "medium": Complexity.MEDIUM,
    "large": Complexity.LARGE,
    "critical": Complexity.CRITICAL,
}


@dataclass
class Estimate:
    """A single agent's complexity estimate for a task."""

    agent: str  # model name or agent id
    complexity: Complexity
    files_estimate: int
    hours_min: float
    hours_max: float
    risk: str  # low/medium/high/critical
    reasoning: str  # WHY this estimate (1-2 sentences)
    confidence: float  # 0.0-1.0


@dataclass
class PokerRound:
    """Result of a planning poker round with multiple estimates."""

    task_description: str
    estimates: List[Estimate] = field(default_factory=list)
    consensus: Optional[Estimate] = None
    divergence_score: float = 0.0
    required_discussion: bool = False
    timestamp: str = ""


def create_estimate(
    agent: str,
    complexity: str,
    files: int,
    hours_min: float,
    hours_max: float,
    risk: str,
    reasoning: str,
    confidence: float = 0.8,
) -> Estimate:
    """Create a typed estimate from raw values.

    Args:
        agent: Model name or agent identifier.
        complexity: Complexity level as string (trivial/small/medium/large/critical).
        files: Estimated number of files affected.
        hours_min: Minimum estimated hours.
        hours_max: Maximum estimated hours.
        risk: Risk level (low/medium/high/critical).
        reasoning: 1-2 sentence explanation for this estimate.
        confidence: Confidence in estimate, 0.0-1.0.

    Returns:
        A typed Estimate dataclass instance.

    Raises:
        ValueError: If complexity string is not recognized or confidence is out of range.
    """
    key = complexity.lower().strip()
    if key not in _COMPLEXITY_MAP:
        raise ValueError(
            f"Unknown complexity '{complexity}'. "
            f"Valid: {list(_COMPLEXITY_MAP.keys())}"
        )
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"Confidence must be 0.0-1.0, got {confidence}")
    if hours_min > hours_max:
        raise ValueError(
            f"hours_min ({hours_min}) must be <= hours_max ({hours_max})"
        )

    return Estimate(
        agent=agent,
        complexity=_COMPLEXITY_MAP[key],
        files_estimate=files,
        hours_min=hours_min,
        hours_max=hours_max,
        risk=risk.lower().strip(),
        reasoning=reasoning,
        confidence=max(0.0, min(1.0, confidence)),
    )


def detect_divergence(estimates: List[Estimate]) -> Tuple[float, str]:
    """Calculate divergence score and explain why estimates differ.

    The divergence score is the ratio of the highest to lowest complexity
    value among the estimates.

    Args:
        estimates: List of estimates to compare.

    Returns:
        Tuple of (score, explanation).
        - score 1.0: perfect agreement
        - score 1.5: minor differences (normal)
        - score 2.0-3.0: significant disagreement (discuss)
        - score 3.0+: major disagreement (human needed)
    """
    if not estimates:
        return 1.0, "No estimates to compare."

    if len(estimates) == 1:
        return 1.0, "Single estimate — no divergence possible."

    values = [e.complexity.value for e in estimates]
    min_val = min(values)
    max_val = max(values)

    if min_val == 0:
        # Should not happen with our enum (starts at 1), but guard anyway.
        score = float(max_val) if max_val > 0 else 1.0
    else:
        score = max_val / min_val

    # Build explanation
    parts: List[str] = []
    if score <= 1.0:
        parts.append("All agents agree on complexity.")
    else:
        agent_levels = [
            f"{e.agent}: {e.complexity.name}" for e in estimates
        ]
        parts.append(f"Estimates span from {Complexity(min_val).name} to {Complexity(max_val).name}.")
        parts.append("Agent breakdown: " + ", ".join(agent_levels) + ".")

        # Identify specific disagreements
        confidences = [e.confidence for e in estimates]
        if max(confidences) - min(confidences) > 0.3:
            parts.append(
                "Confidence levels vary significantly "
                f"({min(confidences):.2f} to {max(confidences):.2f})."
            )

        file_estimates = [e.files_estimate for e in estimates]
        if max(file_estimates) > 2 * min(file_estimates) and min(file_estimates) > 0:
            parts.append(
                f"File estimates range widely ({min(file_estimates)} to {max(file_estimates)})."
            )

    return round(score, 2), " ".join(parts)


def build_consensus(estimates: List[Estimate], divergence: float) -> Estimate:
    """Build consensus estimate from multiple estimates.

    Strategy depends on divergence level:
    - Low divergence (<=1.5): median of all values.
    - Moderate divergence (1.5-3.0): confidence-weighted average.
    - High divergence (>3.0): take the MOST CONSERVATIVE estimate (safety-first).

    Args:
        estimates: List of estimates to reconcile.
        divergence: Divergence score from detect_divergence().

    Returns:
        A consensus Estimate with agent="consensus".

    Raises:
        ValueError: If estimates list is empty.
    """
    if not estimates:
        raise ValueError("Cannot build consensus from empty estimates list.")

    if len(estimates) == 1:
        e = estimates[0]
        return Estimate(
            agent="consensus",
            complexity=e.complexity,
            files_estimate=e.files_estimate,
            hours_min=e.hours_min,
            hours_max=e.hours_max,
            risk=e.risk,
            reasoning=f"Single estimate from {e.agent}.",
            confidence=e.confidence,
        )

    if divergence > 3.0:
        # High divergence: take the most conservative (highest complexity)
        most_conservative = max(estimates, key=lambda e: e.complexity.value)
        return Estimate(
            agent="consensus",
            complexity=most_conservative.complexity,
            files_estimate=max(e.files_estimate for e in estimates),
            hours_min=max(e.hours_min for e in estimates),
            hours_max=max(e.hours_max for e in estimates),
            risk=_most_severe_risk([e.risk for e in estimates]),
            reasoning=(
                f"High divergence ({divergence:.1f}x) — using most conservative "
                f"estimate from {most_conservative.agent}."
            ),
            confidence=min(e.confidence for e in estimates),
        )

    if divergence > 1.5:
        # Moderate divergence: confidence-weighted average
        total_confidence = sum(e.confidence for e in estimates)
        if total_confidence == 0:
            total_confidence = 1.0  # avoid division by zero

        weighted_complexity = sum(
            e.complexity.value * e.confidence for e in estimates
        ) / total_confidence
        weighted_files = sum(
            e.files_estimate * e.confidence for e in estimates
        ) / total_confidence
        weighted_hours_min = sum(
            e.hours_min * e.confidence for e in estimates
        ) / total_confidence
        weighted_hours_max = sum(
            e.hours_max * e.confidence for e in estimates
        ) / total_confidence

        # Round complexity to nearest valid level
        complexity_val = max(1, min(5, round(weighted_complexity)))

        return Estimate(
            agent="consensus",
            complexity=Complexity(complexity_val),
            files_estimate=round(weighted_files),
            hours_min=round(weighted_hours_min, 1),
            hours_max=round(weighted_hours_max, 1),
            risk=_most_severe_risk([e.risk for e in estimates]),
            reasoning=(
                f"Moderate divergence ({divergence:.1f}x) — "
                f"confidence-weighted average across {len(estimates)} agents."
            ),
            confidence=round(
                sum(e.confidence for e in estimates) / len(estimates), 2
            ),
        )

    # Low divergence: median values
    complexities = sorted(e.complexity.value for e in estimates)
    files_sorted = sorted(e.files_estimate for e in estimates)
    hours_min_sorted = sorted(e.hours_min for e in estimates)
    hours_max_sorted = sorted(e.hours_max for e in estimates)

    median_complexity = max(1, min(5, round(statistics.median(complexities))))

    return Estimate(
        agent="consensus",
        complexity=Complexity(median_complexity),
        files_estimate=round(statistics.median(files_sorted)),
        hours_min=round(statistics.median(hours_min_sorted), 1),
        hours_max=round(statistics.median(hours_max_sorted), 1),
        risk=_median_risk([e.risk for e in estimates]),
        reasoning=(
            f"Low divergence ({divergence:.1f}x) — "
            f"median of {len(estimates)} agents."
        ),
        confidence=round(
            sum(e.confidence for e in estimates) / len(estimates), 2
        ),
    )


_RISK_ORDER = ["low", "medium", "high", "critical"]


def _risk_rank(risk: str) -> int:
    """Get numeric rank for a risk level string."""
    try:
        return _RISK_ORDER.index(risk.lower().strip())
    except ValueError:
        return 1  # default to medium if unknown


def _most_severe_risk(risks: List[str]) -> str:
    """Return the most severe risk from a list."""
    if not risks:
        return "medium"
    return max(risks, key=_risk_rank)


def _median_risk(risks: List[str]) -> str:
    """Return the median risk from a list."""
    if not risks:
        return "medium"
    ranked = sorted(risks, key=_risk_rank)
    mid = len(ranked) // 2
    return ranked[mid]


def run_poker_round(task: str, estimates: List[Estimate]) -> PokerRound:
    """Run a planning poker round: compare estimates, detect divergence, build consensus.

    Args:
        task: Description of the task being estimated.
        estimates: List of independent estimates from different agents.

    Returns:
        A PokerRound with divergence analysis and consensus estimate.
    """
    divergence_score, _explanation = detect_divergence(estimates)
    consensus = build_consensus(estimates, divergence_score) if estimates else None

    return PokerRound(
        task_description=task,
        estimates=estimates,
        consensus=consensus,
        divergence_score=divergence_score,
        required_discussion=divergence_score > 2.0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def calculate_accuracy(estimated: Estimate, actual: Dict) -> Dict:
    """Compare estimate vs actual results.

    Args:
        estimated: The original estimate.
        actual: Dict with keys: files (int), hours (float), complexity (str).

    Returns:
        Dict with files_accuracy, hours_accuracy, complexity_match, overall_accuracy.
        All accuracy values are 0.0-1.0.
    """
    actual_files = actual.get("files", 0)
    actual_hours = actual.get("hours", 0.0)
    actual_complexity = actual.get("complexity", "")

    # Files accuracy: 1.0 - |estimated - actual| / max(estimated, actual, 1)
    max_files = max(estimated.files_estimate, actual_files, 1)
    files_accuracy = 1.0 - abs(estimated.files_estimate - actual_files) / max_files

    # Hours accuracy: 1.0 if actual within range, decay otherwise
    if estimated.hours_min <= actual_hours <= estimated.hours_max:
        hours_accuracy = 1.0
    else:
        # Distance from nearest bound
        if actual_hours < estimated.hours_min:
            distance = estimated.hours_min - actual_hours
            reference = max(estimated.hours_min, 1.0)
        else:
            distance = actual_hours - estimated.hours_max
            reference = max(estimated.hours_max, 1.0)
        hours_accuracy = max(0.0, 1.0 - distance / reference)

    # Complexity match: exact match = 1.0, adjacent = 0.5, otherwise 0.0
    complexity_match = 0.0
    actual_key = actual_complexity.lower().strip()
    if actual_key in _COMPLEXITY_MAP:
        actual_val = _COMPLEXITY_MAP[actual_key].value
        diff = abs(estimated.complexity.value - actual_val)
        if diff == 0:
            complexity_match = 1.0
        elif diff == 1:
            complexity_match = 0.5
        else:
            complexity_match = 0.0

    # Overall: weighted average
    overall = (
        files_accuracy * 0.30
        + hours_accuracy * 0.30
        + complexity_match * 0.40
    )

    return {
        "files_accuracy": round(files_accuracy, 3),
        "hours_accuracy": round(hours_accuracy, 3),
        "complexity_match": round(complexity_match, 3),
        "overall_accuracy": round(overall, 3),
    }


def format_poker_table(poker_round: PokerRound) -> str:
    """Format poker round as a readable markdown table.

    Returns:
        Multi-line markdown string with estimate table, divergence,
        and consensus summary.
    """
    lines: List[str] = []
    lines.append("## Planning Poker Results")
    lines.append("")
    lines.append(f"**Task**: {poker_round.task_description}")
    lines.append("")

    # Estimates table
    lines.append("| Agent | Complexity | Files | Hours | Risk | Confidence |")
    lines.append("|-------|-----------|-------|-------|------|------------|")
    for e in poker_round.estimates:
        lines.append(
            f"| {e.agent} | {e.complexity.name} | {e.files_estimate} | "
            f"{e.hours_min}-{e.hours_max}h | {e.risk} | {e.confidence:.2f} |"
        )

    lines.append("")

    # Divergence
    div = poker_round.divergence_score
    if div <= 1.5:
        div_label = "LOW"
    elif div <= 3.0:
        div_label = "MODERATE"
    else:
        div_label = "HIGH"

    discussion = " -- discussion required" if poker_round.required_discussion else ""
    lines.append(f"**Divergence**: {div:.2f}x ({div_label}{discussion})")

    # Consensus
    if poker_round.consensus:
        c = poker_round.consensus
        lines.append("")
        lines.append(
            f"**Consensus**: {c.complexity.name}, "
            f"{c.files_estimate} files, "
            f"{c.hours_min}-{c.hours_max}h, "
            f"{c.risk} risk "
            f"(confidence: {c.confidence:.2f})"
        )
        lines.append(f"**Reasoning**: {c.reasoning}")

    return "\n".join(lines)


def _estimate_to_dict(estimate: Estimate) -> Dict:
    """Convert an Estimate to a JSON-serializable dict."""
    d = asdict(estimate)
    d["complexity"] = estimate.complexity.name
    return d


def _poker_round_to_dict(poker_round: PokerRound) -> Dict:
    """Convert a PokerRound to a JSON-serializable dict."""
    return {
        "task_description": poker_round.task_description,
        "estimates": [_estimate_to_dict(e) for e in poker_round.estimates],
        "consensus": _estimate_to_dict(poker_round.consensus) if poker_round.consensus else None,
        "divergence_score": poker_round.divergence_score,
        "required_discussion": poker_round.required_discussion,
        "timestamp": poker_round.timestamp,
    }


def save_poker_round(poker_round: PokerRound, filepath: str) -> None:
    """Append poker round to JSONL file for historical tracking.

    Args:
        poker_round: The completed poker round to save.
        filepath: Path to the JSONL file (created if it does not exist).
    """
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    record = _poker_round_to_dict(poker_round)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_agent_accuracy_history(agent: str, filepath: str) -> Dict:
    """Get historical accuracy stats for an agent from poker round records.

    Scans saved poker rounds for entries where calculate_accuracy was recorded
    and computes aggregate statistics.

    Args:
        agent: Agent identifier to filter by.
        filepath: Path to the JSONL file with poker round records.

    Returns:
        Dict with rounds_played, avg_accuracy, bias_direction, calibration_factor.
        If no data exists, returns zeroed stats.
    """
    result = {
        "agent": agent,
        "rounds_played": 0,
        "avg_accuracy": 0.0,
        "bias_direction": "none",  # over/under/none
        "calibration_factor": 1.0,
    }

    if not os.path.exists(filepath):
        return result

    rounds_data: List[Dict] = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                rounds_data.append(record)
    except (json.JSONDecodeError, OSError):
        return result

    # Count rounds where this agent participated
    agent_estimates: List[Dict] = []
    for record in rounds_data:
        for est in record.get("estimates", []):
            if est.get("agent") == agent:
                agent_estimates.append(est)

    result["rounds_played"] = len(agent_estimates)

    if not agent_estimates:
        return result

    # If accuracy data is embedded, compute averages
    accuracies = [
        est["accuracy"]["overall_accuracy"]
        for est in agent_estimates
        if "accuracy" in est
    ]

    if accuracies:
        result["avg_accuracy"] = round(sum(accuracies) / len(accuracies), 3)

    # Determine bias from complexity estimates vs actuals
    complexity_diffs: List[int] = []
    for est in agent_estimates:
        if "actual_complexity" in est:
            est_val = _COMPLEXITY_MAP.get(est["complexity"].lower(), Complexity.MEDIUM).value
            act_val = _COMPLEXITY_MAP.get(est["actual_complexity"].lower(), Complexity.MEDIUM).value
            complexity_diffs.append(est_val - act_val)

    if complexity_diffs:
        avg_diff = sum(complexity_diffs) / len(complexity_diffs)
        if avg_diff > 0.3:
            result["bias_direction"] = "over"
            result["calibration_factor"] = round(1.0 - avg_diff * 0.1, 2)
        elif avg_diff < -0.3:
            result["bias_direction"] = "under"
            result["calibration_factor"] = round(1.0 + abs(avg_diff) * 0.1, 2)
        else:
            result["bias_direction"] = "none"
            result["calibration_factor"] = 1.0

    return result
