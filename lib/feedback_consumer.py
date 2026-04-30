# SCOPE: os-only
"""
Feedback Consumer — closes the learning loop by reading captured feedback signals.

Reads the last N entries from .cognitive-os/metrics/prompt-captures.jsonl,
groups them by classification, and surfaces negative/correction/escalation
signals as candidate skill improvement inputs for /self-improve and
/analyze-improvements.

Inspired by: Hermes _SKILL_REVIEW_PROMPT + feedback accumulation pattern.
Called by: skills/analyze-improvements/SKILL.md (Step 0), skills/self-improve/SKILL.md
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

# Categories that warrant skill improvement investigation
ACTIONABLE_CATEGORIES = {"feedback", "correction", "escalation"}

# Prompt-classifier category → human-readable label
CATEGORY_LABELS: Dict[str, str] = {
    "feedback": "User feedback (positive or negative)",
    "correction": "Correction / redirect",
    "escalation": "Escalation (user took over)",
    "task_request": "Task request",
    "context": "Context / informational",
    "decision": "Decision / approval",
}

# Minimum confidence threshold to include an entry as a signal
_MIN_CONFIDENCE = 0.5


def _default_metrics_dir() -> str:
    """Resolve the metrics directory relative to the project root."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return os.path.join(project_dir, ".cognitive-os", "metrics")


def _read_jsonl(path: str, max_lines: int = 500) -> List[Dict[str, Any]]:
    """Read last *max_lines* entries from a JSONL file, newest-last order."""
    if not os.path.exists(path):
        return []
    entries: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return []
    return entries[-max_lines:]


def read_recent_feedback(
    limit: int = 50,
    metrics_dir: str | None = None,
) -> List[Dict[str, Any]]:
    """Read the last *limit* entries from prompt-captures.jsonl.

    Returns a list of dicts in chronological order (oldest first).
    Each dict has at minimum: timestamp, category, confidence, prompt_length.
    """
    if metrics_dir is None:
        metrics_dir = _default_metrics_dir()
    path = os.path.join(metrics_dir, "prompt-captures.jsonl")
    all_entries = _read_jsonl(path, max_lines=max(limit, 500))
    return all_entries[-limit:]


def group_by_classification(
    entries: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Group entries by their *category* field.

    Returns a dict mapping category → list of entries (newest-last order).
    Unknown categories are collected under 'other'.
    """
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        cat = entry.get("category", "other")
        groups.setdefault(cat, []).append(entry)
    return groups


def surface_actionable(
    grouped: Dict[str, List[Dict[str, Any]]],
    min_confidence: float = _MIN_CONFIDENCE,
) -> List[Dict[str, Any]]:
    """Filter grouped entries to actionable signals for skill improvement.

    Actionable categories: 'feedback', 'correction', 'escalation'.
    Each returned dict is an augmented entry with:
        - original fields intact
        - 'signal_category': human-readable label
        - 'is_actionable': True
        - 'recency_rank': position among actionable entries (1 = most recent)

    Entries with confidence < min_confidence are excluded.
    Results are sorted most-recent-first.
    """
    candidates: List[Dict[str, Any]] = []
    for cat, entries in grouped.items():
        if cat not in ACTIONABLE_CATEGORIES:
            continue
        for entry in entries:
            if entry.get("confidence", 0.0) >= min_confidence:
                augmented = dict(entry)
                augmented["signal_category"] = CATEGORY_LABELS.get(cat, cat)
                augmented["is_actionable"] = True
                candidates.append(augmented)

    # Sort newest first using timestamp string (ISO-8601 sorts lexicographically)
    candidates.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    for rank, entry in enumerate(candidates, start=1):
        entry["recency_rank"] = rank

    return candidates


def summarise_for_skill_improvement(
    limit: int = 50,
    metrics_dir: str | None = None,
) -> Dict[str, Any]:
    """High-level helper: read → group → surface → summarise.

    Returns a dict suitable for embedding in an /analyze-improvements or
    /self-improve prompt:
        - total_entries: int
        - actionable_count: int
        - by_category: {category: count} for all entries
        - actionable_signals: list of actionable entries (most recent first)
        - period: {from: ISO, to: ISO} of the sampled window
        - data_source: path to prompt-captures.jsonl
    """
    if metrics_dir is None:
        metrics_dir = _default_metrics_dir()

    entries = read_recent_feedback(limit=limit, metrics_dir=metrics_dir)
    grouped = group_by_classification(entries)
    actionable = surface_actionable(grouped)

    by_category = {cat: len(lst) for cat, lst in grouped.items()}

    timestamps = [e.get("timestamp", "") for e in entries if e.get("timestamp")]
    period_from = min(timestamps) if timestamps else ""
    period_to = max(timestamps) if timestamps else ""

    return {
        "total_entries": len(entries),
        "actionable_count": len(actionable),
        "by_category": by_category,
        "actionable_signals": actionable,
        "period": {"from": period_from, "to": period_to},
        "data_source": os.path.join(metrics_dir, "prompt-captures.jsonl"),
    }
