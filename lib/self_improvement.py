# SCOPE: os-only
"""Self-improvement analysis — minimal viable version.

Reads KPI history and session learnings to suggest improvements.
NEVER auto-applies changes — only suggests.
"""
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional


def _read_jsonl(path: str, max_lines: int = 500) -> List[Dict[str, Any]]:
    """Read a JSONL file, returning up to max_lines entries."""
    if not os.path.exists(path):
        return []
    entries = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        pass
    return entries


def analyze_kpi_history(metrics_dir: str = ".cognitive-os/metrics") -> Dict[str, Any]:
    """Analyze KPI history and session learnings to produce a summary.

    Returns dict with: trust_scores, success_rate, error_types, total_entries, etc.
    """
    kpi_entries = _read_jsonl(os.path.join(metrics_dir, "kpi-history.jsonl"))
    session_entries = _read_jsonl(os.path.join(metrics_dir, "session-learnings.jsonl"))
    skill_entries = _read_jsonl(os.path.join(metrics_dir, "skill-archive.jsonl"))
    error_entries = _read_jsonl(os.path.join(metrics_dir, "error-learning.jsonl"))
    consequence_entries = _read_jsonl(os.path.join(metrics_dir, "consequence-history.jsonl"))

    # Trust scores from consequence history (most reliable source)
    trust_scores = [
        e.get("trust_score", 0)
        for e in consequence_entries
        if isinstance(e.get("trust_score"), (int, float)) and e["trust_score"] != 75
    ]
    # If all scores are 75 (hardcoded default), include them but flag it
    all_scores = [
        e.get("trust_score", 0)
        for e in consequence_entries
        if isinstance(e.get("trust_score"), (int, float))
    ]
    scores_are_real = len(trust_scores) > 0
    effective_scores = trust_scores if scores_are_real else all_scores

    avg_trust = sum(effective_scores) / len(effective_scores) if effective_scores else 0

    # Success rate from consequence history
    total_completions = len(consequence_entries)
    successes = sum(1 for e in consequence_entries if e.get("success", False))
    success_rate = (successes / total_completions * 100) if total_completions > 0 else 0

    # Error type distribution
    error_types: Dict[str, int] = {}
    for e in error_entries:
        etype = e.get("error_type", e.get("type", "unknown"))
        error_types[etype] = error_types.get(etype, 0) + 1

    # Error recurrence (same type+service 3+ times)
    error_keys: Dict[str, int] = {}
    for e in error_entries:
        key = f"{e.get('type', 'unknown')}:{e.get('service', 'unknown')}"
        error_keys[key] = error_keys.get(key, 0) + 1
    recurring_errors = {k: v for k, v in error_keys.items() if v >= 3}

    # Skill health from skill archive
    skill_failures: Dict[str, int] = {}
    for e in skill_entries:
        name = e.get("skill_name", "")
        if name and not e.get("success", True):
            skill_failures[name] = skill_failures.get(name, 0) + 1

    # Consequence distribution
    consequences: Dict[str, int] = {}
    for e in consequence_entries:
        c = e.get("consequence", "unknown")
        consequences[c] = consequences.get(c, 0) + 1

    return {
        "avg_trust_score": round(avg_trust, 1),
        "trust_scores_are_real": scores_are_real,
        "success_rate": round(success_rate, 1),
        "total_completions": total_completions,
        "total_successes": successes,
        "total_errors": len(error_entries),
        "error_types": error_types,
        "recurring_errors": recurring_errors,
        "skill_failures": skill_failures,
        "consequences": consequences,
        "data_sources": {
            "kpi_entries": len(kpi_entries),
            "session_entries": len(session_entries),
            "skill_entries": len(skill_entries),
            "error_entries": len(error_entries),
            "consequence_entries": len(consequence_entries),
        },
    }


def suggest_improvements(analysis: Dict[str, Any]) -> List[str]:
    """Generate actionable suggestions based on analysis. Never auto-applies."""
    suggestions = []

    if not analysis.get("trust_scores_are_real", False):
        suggestions.append(
            "CRITICAL: Trust scores are all default (75). record_completion.py is not "
            "extracting real scores from agent output. Fix the signal pipeline first."
        )

    avg = analysis.get("avg_trust_score", 0)
    if avg > 0 and avg < 75:
        suggestions.append(
            f"Average trust score is {avg}/100 (target: >75). "
            "Improve acceptance criteria in agent prompts to boost verification evidence."
        )

    rate = analysis.get("success_rate", 0)
    if rate > 0 and rate < 85:
        suggestions.append(
            f"Success rate is {rate}% (target: >85%). "
            "Review failing skills with /optimize-skill to identify patterns."
        )

    recurring = analysis.get("recurring_errors", {})
    if recurring:
        top = sorted(recurring.items(), key=lambda x: -x[1])[:3]
        patterns = ", ".join(f"{k} ({v}x)" for k, v in top)
        suggestions.append(
            f"Recurring error patterns detected: {patterns}. "
            "Run /error-analyzer to investigate root causes."
        )

    skill_failures = analysis.get("skill_failures", {})
    if skill_failures:
        top = sorted(skill_failures.items(), key=lambda x: -x[1])[:3]
        skills = ", ".join(f"{k} ({v} failures)" for k, v in top)
        suggestions.append(
            f"Skills with repeated failures: {skills}. "
            "Consider running /optimize-skill on these."
        )

    consequences = analysis.get("consequences", {})
    if consequences.get("maintain", 0) > 0 and not any(
        consequences.get(c, 0) > 0 for c in ("promote", "warn", "degrade", "disable")
    ):
        suggestions.append(
            "Consequence engine shows ONLY 'maintain' actions — no promotions or degradations. "
            "This means the feedback loop is dead. Fix trust score extraction to activate it."
        )

    total = analysis.get("total_completions", 0)
    if total == 0:
        suggestions.append(
            "No completion data found. Ensure completion-gate.sh is wired and "
            "record_completion.py is being called."
        )

    return suggestions


def format_improvement_report(
    analysis: Dict[str, Any], suggestions: Optional[List[str]] = None
) -> str:
    """Markdown report with metrics and suggestions."""
    if suggestions is None:
        suggestions = suggest_improvements(analysis)

    ds = analysis.get("data_sources", {})
    lines = [
        "# Self-Improvement Report",
        "",
        "## Data Sources",
        f"- KPI history: {ds.get('kpi_entries', 0)} entries",
        f"- Session learnings: {ds.get('session_entries', 0)} entries",
        f"- Skill archive: {ds.get('skill_entries', 0)} entries",
        f"- Error learning: {ds.get('error_entries', 0)} entries",
        f"- Consequence history: {ds.get('consequence_entries', 0)} entries",
        "",
        "## Metrics",
        f"- Average trust score: {analysis.get('avg_trust_score', 'N/A')}",
        f"- Trust scores are real: {'Yes' if analysis.get('trust_scores_are_real') else 'NO — still hardcoded defaults'}",
        f"- Success rate: {analysis.get('success_rate', 'N/A')}%",
        f"- Total completions: {analysis.get('total_completions', 0)}",
        f"- Total errors: {analysis.get('total_errors', 0)}",
        f"- Recurring errors: {len(analysis.get('recurring_errors', {}))}",
        "",
    ]

    if suggestions:
        lines.append("## Suggestions")
        for i, s in enumerate(suggestions, 1):
            lines.append(f"{i}. {s}")
    else:
        lines.append("## Status: Healthy")
        lines.append("No improvements suggested at this time.")

    return "\n".join(lines)
