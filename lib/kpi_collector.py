# SCOPE: os-only
"""KPI Collector -- Reads metric JSONL files and computes session KPIs.

Computes the KPIs defined in rules/agent-kpis.md by reading the .jsonl
metric files produced by hooks (skill-metrics, error-learning,
trust-scores, escalation-events, hallucinations, etc.).

KPIs produced:
    - Agent Quality: average trust score (target >90%)
    - First-attempt success rate (from skill-metrics)
    - Error recurrence count (from error-learning)
    - Escalation rate (5-15% healthy range)
    - Hallucination rate
    - Total cost

Usage:
    from lib.kpi_collector import collect_session_kpis, format_kpi_dashboard

    kpis = collect_session_kpis("/path/to/metrics")
    print(format_kpi_dashboard(kpis))

Python 3.9+ compatible. No external dependencies.
Author: luum
"""

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# JSONL reader helper
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read a JSONL file and return a list of parsed dicts.

    Silently skips malformed lines and returns an empty list if the file
    does not exist.
    """
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


# ---------------------------------------------------------------------------
# Individual KPI computations
# ---------------------------------------------------------------------------


def _compute_trust_score_kpis(
    trust_scores: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute trust-score related KPIs.

    Returns:
        avg_trust_score: mean score across all entries.
        trust_score_count: number of entries.
        self_awareness_rate: % of reports with uncertainties > 0.
    """
    if not trust_scores:
        return {
            "avg_trust_score": 0.0,
            "trust_score_count": 0,
            "self_awareness_rate": 0.0,
        }

    scores = [float(e.get("score", e.get("trust_score", 0))) for e in trust_scores]
    avg = sum(scores) / len(scores) if scores else 0.0

    # Self-awareness: entries that declare uncertainties
    awareness_count = sum(
        1 for e in trust_scores
        if int(e.get("uncertainties_count", e.get("uncertainties", 0))) > 0
    )
    awareness_rate = (awareness_count / len(trust_scores) * 100) if trust_scores else 0.0

    return {
        "avg_trust_score": round(avg, 1),
        "trust_score_count": len(scores),
        "self_awareness_rate": round(awareness_rate, 1),
    }


def _compute_skill_metrics_kpis(
    skill_metrics: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute skill-metrics KPIs.

    Returns:
        total_executions: total skill invocations.
        successful_executions: count where success=True.
        first_attempt_success_rate: % of first-attempt successes.
    """
    if not skill_metrics:
        return {
            "total_executions": 0,
            "successful_executions": 0,
            "first_attempt_success_rate": 0.0,
        }

    total = len(skill_metrics)
    successes = sum(1 for e in skill_metrics if e.get("success", False))
    rate = (successes / total * 100) if total > 0 else 0.0

    return {
        "total_executions": total,
        "successful_executions": successes,
        "first_attempt_success_rate": round(rate, 1),
    }


def _compute_error_kpis(
    error_entries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute error-learning KPIs.

    Returns:
        total_errors: total error entries.
        error_types: counter of error types.
        recurrence_count: number of error types that appeared 3+ times.
    """
    if not error_entries:
        return {
            "total_errors": 0,
            "error_types": {},
            "recurrence_count": 0,
        }

    type_counts = Counter(e.get("type", "UNKNOWN") for e in error_entries)
    recurrence = sum(1 for count in type_counts.values() if count >= 3)

    return {
        "total_errors": len(error_entries),
        "error_types": dict(type_counts),
        "recurrence_count": recurrence,
    }


def _compute_escalation_kpis(
    escalation_events: List[Dict[str, Any]],
    total_agent_completions: int,
) -> Dict[str, Any]:
    """Compute escalation-related KPIs.

    Returns:
        escalation_count: total escalation events.
        escalation_rate: escalations / total completions (%).
        escalation_rate_status: HEALTHY / LOW / HIGH.
    """
    count = len(escalation_events)
    rate = (count / total_agent_completions * 100) if total_agent_completions > 0 else 0.0

    if rate < 5:
        status = "LOW"
    elif rate <= 15:
        status = "HEALTHY"
    else:
        status = "HIGH"

    return {
        "escalation_count": count,
        "escalation_rate": round(rate, 1),
        "escalation_rate_status": status,
    }


def _compute_hallucination_kpis(
    hallucination_entries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute hallucination KPIs.

    Returns:
        total_checks: total hallucination check entries.
        total_hallucinations: sum of hallucination counts.
        total_verified: sum of verified claims.
        hallucination_rate: hallucinations / (hallucinations + verified) %.
    """
    if not hallucination_entries:
        return {
            "total_checks": 0,
            "total_hallucinations": 0,
            "total_verified": 0,
            "hallucination_rate": 0.0,
        }

    total_h = sum(int(e.get("hallucinations", 0)) for e in hallucination_entries)
    total_v = sum(int(e.get("verified", 0)) for e in hallucination_entries)
    denom = total_h + total_v
    rate = (total_h / denom * 100) if denom > 0 else 0.0

    return {
        "total_checks": len(hallucination_entries),
        "total_hallucinations": total_h,
        "total_verified": total_v,
        "hallucination_rate": round(rate, 1),
    }


# ---------------------------------------------------------------------------
# Main collection function
# ---------------------------------------------------------------------------


def collect_session_kpis(metrics_dir: str) -> Dict[str, Any]:
    """Read all metric JSONL files and compute session KPIs.

    Args:
        metrics_dir: Path to the metrics directory (e.g. ".cognitive-os/metrics"
            or ".claude/metrics").

    Returns:
        A dict with all computed KPI values, keyed by category.
    """
    base = Path(metrics_dir)

    # Read metric files
    trust_scores = _read_jsonl(base / "trust-scores.jsonl")
    skill_metrics = _read_jsonl(base / "skill-metrics.jsonl")
    error_entries = _read_jsonl(base / "error-learning.jsonl")
    escalation_events = _read_jsonl(base / "escalation-events.jsonl")
    hallucinations = _read_jsonl(base / "hallucinations.jsonl")
    consequence_history = _read_jsonl(base / "consequence-history.jsonl")

    # Use skill-metrics total as proxy for total agent completions.
    total_completions = len(skill_metrics)

    # Compute individual KPI groups
    trust_kpis = _compute_trust_score_kpis(trust_scores)
    skill_kpis = _compute_skill_metrics_kpis(skill_metrics)
    error_kpis = _compute_error_kpis(error_entries)
    escalation_kpis = _compute_escalation_kpis(escalation_events, total_completions)
    hallucination_kpis = _compute_hallucination_kpis(hallucinations)

    # Cost from consequence history performance records
    cost_entries = [
        e for e in consequence_history
        if e.get("record_type") == "performance"
    ]
    total_cost = sum(float(e.get("cost_usd", 0)) for e in cost_entries)

    # Overall quality composite (weighted)
    # If we have trust scores, use them; otherwise fall back to success rate.
    if trust_kpis["trust_score_count"] > 0:
        quality_score = trust_kpis["avg_trust_score"]
    else:
        quality_score = skill_kpis["first_attempt_success_rate"]

    quality_status = (
        "ON_TRACK" if quality_score >= 90
        else "AT_RISK" if quality_score >= 75
        else "BEHIND"
    )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trust": trust_kpis,
        "skills": skill_kpis,
        "errors": error_kpis,
        "escalations": escalation_kpis,
        "hallucinations": hallucination_kpis,
        "cost": {
            "total_usd": round(total_cost, 4),
        },
        "quality": {
            "composite_score": round(quality_score, 1),
            "status": quality_status,
            "target": 90.0,
        },
    }


# ---------------------------------------------------------------------------
# Dashboard formatting
# ---------------------------------------------------------------------------


def format_kpi_dashboard(kpis: Dict[str, Any]) -> str:
    """Format KPI data as a human-readable dashboard.

    Args:
        kpis: The dict returned by collect_session_kpis.

    Returns:
        A multi-line string suitable for terminal display.
    """
    lines: List[str] = []
    lines.append("AGENT KPI DASHBOARD")
    lines.append("=" * 50)
    lines.append("")

    # Quality
    q = kpis.get("quality", {})
    lines.append(f"QUALITY: {q.get('composite_score', 0)}% "
                 f"(target {q.get('target', 90)}%) -- {q.get('status', 'UNKNOWN')}")
    lines.append("")

    # Trust
    t = kpis.get("trust", {})
    lines.append("TRUST SCORES:")
    lines.append(f"  Avg trust score:     {t.get('avg_trust_score', 0)}%")
    lines.append(f"  Reports count:       {t.get('trust_score_count', 0)}")
    lines.append(f"  Self-awareness rate: {t.get('self_awareness_rate', 0)}%")
    lines.append("")

    # Skills
    s = kpis.get("skills", {})
    lines.append("SKILL EXECUTION:")
    lines.append(f"  Total executions:         {s.get('total_executions', 0)}")
    lines.append(f"  Successful:               {s.get('successful_executions', 0)}")
    lines.append(f"  First-attempt success:    {s.get('first_attempt_success_rate', 0)}%")
    lines.append("")

    # Errors
    e = kpis.get("errors", {})
    lines.append("ERRORS:")
    lines.append(f"  Total errors:       {e.get('total_errors', 0)}")
    lines.append(f"  Recurring (3+):     {e.get('recurrence_count', 0)}")
    if e.get("error_types"):
        for etype, count in sorted(e["error_types"].items(), key=lambda x: -x[1]):
            lines.append(f"    {etype}: {count}")
    lines.append("")

    # Escalations
    esc = kpis.get("escalations", {})
    lines.append("ESCALATIONS:")
    lines.append(f"  Count:   {esc.get('escalation_count', 0)}")
    lines.append(f"  Rate:    {esc.get('escalation_rate', 0)}%")
    lines.append(f"  Status:  {esc.get('escalation_rate_status', 'UNKNOWN')}")
    lines.append("")

    # Hallucinations
    h = kpis.get("hallucinations", {})
    lines.append("HALLUCINATIONS:")
    lines.append(f"  Checks:         {h.get('total_checks', 0)}")
    lines.append(f"  Hallucinations: {h.get('total_hallucinations', 0)}")
    lines.append(f"  Verified:       {h.get('total_verified', 0)}")
    lines.append(f"  Rate:           {h.get('hallucination_rate', 0)}%")
    lines.append("")

    # Cost
    c = kpis.get("cost", {})
    lines.append(f"COST: ${c.get('total_usd', 0):.4f}")

    return "\n".join(lines)
