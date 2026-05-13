# SCOPE: both
# scope: both
"""Estimation calibration loop for Cognitive OS.

Records pre-task estimates and post-task actuals, computes calibration
factors from historical data, and applies corrections to future estimates.

The 5 anti-bias layers:
1. Proxies -- use concrete counts (files, lines, endpoints) not abstract effort
2. Calibration -- historical data adjusts future estimates automatically
3. Multiple estimates -- record min/max ranges, not point estimates
4. Ranges -- calibration preserves and adjusts the range, not just the midpoint
5. Post-mortem -- every completed task feeds back into calibration

Python 3.9+ compatible. No external dependencies.
"""

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# Valid complexity levels matching definition-of-done.md
VALID_COMPLEXITIES = ("trivial", "small", "medium", "large", "critical")

# Default metrics directory (relative to project root)
_DEFAULT_METRICS_DIR = ".cognitive-os/metrics"
_ESTIMATIONS_FILE = "estimations.jsonl"


def _metrics_path(metrics_dir: Optional[str] = None) -> Path:
    """Resolve the estimations JSONL file path."""
    base = Path(metrics_dir) if metrics_dir else Path(_DEFAULT_METRICS_DIR)
    return base / _ESTIMATIONS_FILE


def _read_entries(metrics_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read all entries from the estimations JSONL file."""
    path = _metrics_path(metrics_dir)
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def _append_entry(entry: Dict[str, Any], metrics_dir: Optional[str] = None) -> None:
    """Append an entry to the estimations JSONL file."""
    path = _metrics_path(metrics_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def _update_entry(
    task_id: str,
    updates: Dict[str, Any],
    metrics_dir: Optional[str] = None,
) -> bool:
    """Update an existing entry by task_id. Returns True if found and updated."""
    path = _metrics_path(metrics_dir)
    if not path.exists():
        return False

    entries = _read_entries(metrics_dir)
    found = False
    for entry in entries:
        if entry.get("task_id") == task_id and entry.get("type") == "estimate":
            entry.update(updates)
            found = True
            break

    if found:
        with open(path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, default=str) + "\n")
    return found


def record_estimate(
    task_id: str,
    agent: str,
    estimates: Dict[str, Any],
    metrics_dir: Optional[str] = None,
) -> None:
    """Record a pre-task estimation.

    Args:
        task_id: Unique identifier for the task.
        agent: Name/identifier of the agent making the estimate.
        estimates: Dict with keys:
            - complexity: str (trivial/small/medium/large/critical)
            - effort_hours_min: float (lower bound estimate)
            - effort_hours_max: float (upper bound estimate)
            - risk: str (low/medium/high/critical)
            - files_estimate: int (estimated number of files affected)
        metrics_dir: Optional override for the metrics directory.
    """
    complexity = estimates.get("complexity", "medium")
    if complexity not in VALID_COMPLEXITIES:
        complexity = "medium"

    entry = {
        "type": "estimate",
        "task_id": task_id,
        "agent": agent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "complexity": complexity,
        "effort_hours_min": float(estimates.get("effort_hours_min", 0)),
        "effort_hours_max": float(estimates.get("effort_hours_max", 0)),
        "risk": estimates.get("risk", "medium"),
        "files_estimate": int(estimates.get("files_estimate", 0)),
    }
    _append_entry(entry, metrics_dir)


def record_actual(
    task_id: str,
    actuals: Dict[str, Any],
    metrics_dir: Optional[str] = None,
) -> None:
    """Record post-task actuals and compute accuracy.

    Args:
        task_id: Matching task_id from a prior record_estimate call.
        actuals: Dict with keys:
            - actual_hours: float
            - actual_files: int
            - retries: int (number of retry attempts)
            - bugs_found: int (bugs discovered during implementation)
        metrics_dir: Optional override for the metrics directory.
    """
    entries = _read_entries(metrics_dir)
    estimate_entry = None
    for entry in entries:
        if entry.get("task_id") == task_id and entry.get("type") == "estimate":
            estimate_entry = entry
            break

    actual_hours = float(actuals.get("actual_hours", 0))
    actual_files = int(actuals.get("actual_files", 0))
    retries = int(actuals.get("retries", 0))
    bugs_found = int(actuals.get("bugs_found", 0))

    # Compute accuracy ratios
    effort_accuracy = _compute_accuracy(
        estimate_entry.get("effort_hours_min", 0) if estimate_entry else 0,
        estimate_entry.get("effort_hours_max", 0) if estimate_entry else 0,
        actual_hours,
    )
    files_accuracy = _compute_files_accuracy(
        estimate_entry.get("files_estimate", 0) if estimate_entry else 0,
        actual_files,
    )

    actual_entry = {
        "type": "actual",
        "task_id": task_id,
        "agent": estimate_entry.get("agent", "unknown") if estimate_entry else "unknown",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actual_hours": actual_hours,
        "actual_files": actual_files,
        "retries": retries,
        "bugs_found": bugs_found,
        "effort_accuracy": effort_accuracy,
        "files_accuracy": files_accuracy,
        "had_estimate": estimate_entry is not None,
    }
    _append_entry(actual_entry, metrics_dir)


def _compute_accuracy(
    min_hours: float, max_hours: float, actual: float
) -> float:
    """Compute effort accuracy as a ratio.

    Returns 1.0 if actual falls within the estimate range.
    Returns < 1.0 if underestimated (actual > max).
    Returns > 1.0 if overestimated (actual < min).
    Returns 0.0 if actual is 0 (cannot compute).
    """
    if actual <= 0:
        return 0.0
    if min_hours <= 0 and max_hours <= 0:
        return 0.0

    midpoint = (min_hours + max_hours) / 2.0
    if midpoint <= 0:
        return 0.0

    if min_hours <= actual <= max_hours:
        return 1.0

    # Ratio: estimate_midpoint / actual
    # > 1.0 means overestimate, < 1.0 means underestimate
    return midpoint / actual


def _compute_files_accuracy(estimated: int, actual: int) -> float:
    """Compute file count accuracy as a ratio.

    Returns estimated / actual.
    1.0 = perfect, < 1.0 = underestimated, > 1.0 = overestimated.
    """
    if actual <= 0:
        if estimated <= 0:
            return 1.0  # Both zero = trivially correct
        return 0.0  # Estimated files but actual was 0 — undefined, treat as 0
    if estimated <= 0:
        return 0.0  # Estimated 0 but actual > 0 — total miss
    return float(estimated) / float(actual)


def get_calibration_factor(
    agent: str, metrics_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate calibration factors from historical estimate-vs-actual data.

    Returns:
        Dict with:
            - complexity_bias: float (> 1.0 = underestimates, < 1.0 = overestimates)
            - effort_bias: float (> 1.0 = underestimates effort, < 1.0 = overestimates)
            - files_bias: float (> 1.0 = underestimates files, < 1.0 = overestimates)
            - risk_bias: float (> 1.0 = underestimates risk)
            - sample_size: int (number of data points)
            - confidence: str (none/low/medium/high based on sample size)
    """
    entries = _read_entries(metrics_dir)
    actuals = [
        e for e in entries
        if e.get("type") == "actual"
        and e.get("agent") == agent
        and e.get("had_estimate", False)
    ]

    if not actuals:
        return {
            "complexity_bias": 1.0,
            "effort_bias": 1.0,
            "files_bias": 1.0,
            "risk_bias": 1.0,
            "sample_size": 0,
            "confidence": "none",
        }

    # Compute biases from accuracy ratios
    effort_accuracies = [
        a["effort_accuracy"] for a in actuals
        if a.get("effort_accuracy", 0) > 0
    ]
    files_accuracies = [
        a["files_accuracy"] for a in actuals
        if a.get("files_accuracy", 0) > 0
    ]

    # Effort bias: if agents consistently underestimate (accuracy < 1.0),
    # bias > 1.0 to inflate future estimates
    effort_bias = 1.0
    if effort_accuracies:
        mean_accuracy = statistics.mean(effort_accuracies)
        if mean_accuracy > 0:
            effort_bias = 1.0 / mean_accuracy

    # Files bias: same logic
    files_bias = 1.0
    if files_accuracies:
        mean_accuracy = statistics.mean(files_accuracies)
        if mean_accuracy > 0:
            files_bias = 1.0 / mean_accuracy

    # Risk bias: compute from retries and bugs
    risk_entries = [a for a in actuals if "retries" in a and "bugs_found" in a]
    risk_bias = 1.0
    if risk_entries:
        avg_retries = statistics.mean([a["retries"] for a in risk_entries])
        avg_bugs = statistics.mean([a["bugs_found"] for a in risk_entries])
        # More retries and bugs = underestimated risk
        risk_bias = 1.0 + (avg_retries * 0.1) + (avg_bugs * 0.05)

    # Complexity bias: use the mean of effort and files bias as proxy
    complexity_bias = statistics.mean([effort_bias, files_bias])

    sample_size = len(actuals)
    if sample_size >= 20:
        confidence = "high"
    elif sample_size >= 10:
        confidence = "medium"
    elif sample_size >= 3:
        confidence = "low"
    else:
        confidence = "none"

    return {
        "complexity_bias": round(complexity_bias, 3),
        "effort_bias": round(effort_bias, 3),
        "files_bias": round(files_bias, 3),
        "risk_bias": round(risk_bias, 3),
        "sample_size": sample_size,
        "confidence": confidence,
    }


def apply_calibration(
    estimate: Dict[str, Any],
    agent: str,
    metrics_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Apply calibration factors to a new estimate.

    Returns a new dict with adjusted values and a calibration note.
    The original estimate is not modified.
    """
    factors = get_calibration_factor(agent, metrics_dir)
    result = dict(estimate)

    if factors["sample_size"] < 10:
        result["calibration_applied"] = False
        result["calibration_note"] = (
            f"Insufficient data for calibration ({factors['sample_size']} samples, "
            f"need 10+). Using raw estimate."
        )
        return result

    # Apply effort bias to hours
    effort_bias = factors["effort_bias"]
    if "effort_hours_min" in result:
        result["effort_hours_min"] = round(
            float(result["effort_hours_min"]) * effort_bias, 2
        )
    if "effort_hours_max" in result:
        result["effort_hours_max"] = round(
            float(result["effort_hours_max"]) * effort_bias, 2
        )

    # Apply files bias
    files_bias = factors["files_bias"]
    if "files_estimate" in result:
        result["files_estimate"] = max(
            1, round(int(result["files_estimate"]) * files_bias)
        )

    # Apply risk bias (upgrade risk if bias is high)
    risk_bias = factors["risk_bias"]
    risk_levels = ["low", "medium", "high", "critical"]
    if "risk" in result and risk_bias > 1.5:
        current_idx = risk_levels.index(result["risk"]) if result["risk"] in risk_levels else 1
        new_idx = min(current_idx + 1, len(risk_levels) - 1)
        result["risk"] = risk_levels[new_idx]

    result["calibration_applied"] = True
    result["calibration_note"] = (
        f"Calibrated using {factors['sample_size']} historical data points "
        f"(confidence: {factors['confidence']}). "
        f"Effort bias: {effort_bias:.2f}x, "
        f"Files bias: {files_bias:.2f}x, "
        f"Risk bias: {risk_bias:.2f}x."
    )
    return result


def format_calibration_report(
    agent: str, metrics_dir: Optional[str] = None
) -> str:
    """Generate a human-readable calibration accuracy report for an agent."""
    factors = get_calibration_factor(agent, metrics_dir)
    entries = _read_entries(metrics_dir)
    actuals = [
        e for e in entries
        if e.get("type") == "actual"
        and e.get("agent") == agent
        and e.get("had_estimate", False)
    ]

    lines = [
        f"# Estimation Calibration Report: {agent}",
        "",
        f"**Data points**: {factors['sample_size']}",
        f"**Confidence**: {factors['confidence']}",
        "",
        "## Bias Factors",
        "",
        f"| Factor | Value | Interpretation |",
        f"|--------|-------|----------------|",
        f"| Effort | {factors['effort_bias']:.3f}x | "
        f"{'Underestimates effort' if factors['effort_bias'] > 1.1 else 'Overestimates effort' if factors['effort_bias'] < 0.9 else 'Well calibrated'} |",
        f"| Files | {factors['files_bias']:.3f}x | "
        f"{'Underestimates scope' if factors['files_bias'] > 1.1 else 'Overestimates scope' if factors['files_bias'] < 0.9 else 'Well calibrated'} |",
        f"| Risk | {factors['risk_bias']:.3f}x | "
        f"{'Underestimates risk' if factors['risk_bias'] > 1.2 else 'Well calibrated'} |",
        f"| Complexity | {factors['complexity_bias']:.3f}x | "
        f"{'Underestimates complexity' if factors['complexity_bias'] > 1.1 else 'Overestimates complexity' if factors['complexity_bias'] < 0.9 else 'Well calibrated'} |",
        "",
    ]

    if actuals:
        effort_accs = [a["effort_accuracy"] for a in actuals if a.get("effort_accuracy", 0) > 0]
        files_accs = [a["files_accuracy"] for a in actuals if a.get("files_accuracy", 0) > 0]

        lines.append("## Accuracy Summary")
        lines.append("")
        if effort_accs:
            lines.append(
                f"- **Effort accuracy**: mean={statistics.mean(effort_accs):.2f}, "
                f"median={statistics.median(effort_accs):.2f}"
            )
        if files_accs:
            lines.append(
                f"- **Files accuracy**: mean={statistics.mean(files_accs):.2f}, "
                f"median={statistics.median(files_accs):.2f}"
            )

        total_retries = sum(a.get("retries", 0) for a in actuals)
        total_bugs = sum(a.get("bugs_found", 0) for a in actuals)
        lines.append(f"- **Total retries**: {total_retries}")
        lines.append(f"- **Total bugs found**: {total_bugs}")
        lines.append("")

    if factors["sample_size"] < 10:
        lines.append("## Status")
        lines.append("")
        lines.append(
            f"Need {10 - factors['sample_size']} more data points before "
            f"calibration is auto-applied. Current data is informational only."
        )
        lines.append("")

    return "\n".join(lines)
