# SCOPE: both
# scope: both
"""Claude Usage Reader -- reads ground-truth token usage from Claude Code sessions.

Reads ~/.claude/projects/*.jsonl to get actual token consumption, costs,
and session data. Used for cost reconciliation against our own tracking.

Usage:
    from lib.claude_usage_reader import read_usage, reconcile_costs

    usage = read_usage()  # All sessions
    usage = read_usage(since_hours=24)  # Last 24 hours
    report = reconcile_costs(usage)  # Compare against our cost-events.jsonl
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Model pricing per 1M tokens (same as model_router.py)
MODEL_PRICING = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "claude-haiku-3.5": {"input": 0.25, "output": 1.25},
}


def get_claude_projects_dir() -> Path:
    """Return the Claude Code projects directory."""
    return Path.home() / ".claude" / "projects"


def read_session_file(path: Path) -> list[dict]:
    """Parse a Claude Code JSONL session file, extracting usage entries."""
    entries = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Claude Code logs usage with these fields
                    if "input_tokens" in data or "output_tokens" in data:
                        entries.append(data)
                except json.JSONDecodeError:
                    continue
    except (OSError, IOError) as e:
        logger.warning("Failed to read %s: %s", path, e)
    return entries


def read_usage(
    since_hours: float | None = None,
    project_filter: str | None = None,
) -> list[dict]:
    """Read usage data from all Claude Code session files.

    Args:
        since_hours: Only include entries from the last N hours
        project_filter: Only include entries from projects matching this string

    Returns:
        List of usage entry dicts with: timestamp, input_tokens, output_tokens,
        cache_creation_tokens, cache_read_tokens, model, cost_usd, session_id
    """
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        logger.info("Claude projects dir not found: %s", projects_dir)
        return []

    cutoff = None
    if since_hours is not None:
        cutoff = time.time() - (since_hours * 3600)

    all_entries = []
    for jsonl_file in projects_dir.rglob("*.jsonl"):
        # Skip agent sidechain files
        if jsonl_file.name.startswith("agent-"):
            continue

        # Apply project filter
        if project_filter and project_filter not in str(jsonl_file):
            continue

        entries = read_session_file(jsonl_file)
        for entry in entries:
            # Apply time filter
            if cutoff and entry.get("timestamp"):
                try:
                    ts = datetime.fromisoformat(entry["timestamp"]).timestamp()
                    if ts < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass
            all_entries.append(entry)

    return all_entries


def calculate_cost(entry: dict) -> float:
    """Calculate USD cost for a single usage entry."""
    model = entry.get("model", "")
    input_tokens = entry.get("input_tokens", 0)
    output_tokens = entry.get("output_tokens", 0)

    # Try exact match first, then prefix match
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        for model_key, p in MODEL_PRICING.items():
            if model_key in model:
                pricing = p
                break

    if not pricing:
        return entry.get("cost_usd", 0.0)

    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000


def summarize_usage(entries: list[dict]) -> dict:
    """Summarize usage data into totals."""
    total_input = sum(e.get("input_tokens", 0) for e in entries)
    total_output = sum(e.get("output_tokens", 0) for e in entries)
    total_cost = sum(calculate_cost(e) for e in entries)
    models_used = set(e.get("model", "unknown") for e in entries)

    return {
        "total_entries": len(entries),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cost_usd": round(total_cost, 4),
        "models_used": sorted(models_used),
    }


def reconcile_costs(
    usage_entries: list[dict],
    cost_events_path: str | None = None,
) -> dict:
    """Compare Claude's ground-truth usage against our cost-events.jsonl.

    Returns dict with: ground_truth_cost, tracked_cost, discrepancy, discrepancy_pct
    """
    # Ground truth from Claude
    ground_truth = summarize_usage(usage_entries)

    # Our tracked costs
    if cost_events_path is None:
        cost_events_path = os.path.join(
            os.environ.get("CLAUDE_PROJECT_DIR", "."),
            ".cognitive-os", "metrics", "cost-events.jsonl"
        )

    tracked_cost = 0.0
    try:
        with open(cost_events_path) as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    tracked_cost += event.get("estimated_cost_usd", 0.0)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass

    gt_cost = ground_truth["total_cost_usd"]
    discrepancy = abs(gt_cost - tracked_cost)
    discrepancy_pct = (discrepancy / gt_cost * 100) if gt_cost > 0 else 0

    return {
        "ground_truth_cost_usd": gt_cost,
        "tracked_cost_usd": round(tracked_cost, 4),
        "discrepancy_usd": round(discrepancy, 4),
        "discrepancy_pct": round(discrepancy_pct, 1),
        "entries_analyzed": ground_truth["total_entries"],
        "models_used": ground_truth["models_used"],
    }


def format_reconciliation_report(report: dict) -> str:
    """Format a human-readable reconciliation report."""
    lines = [
        "COST RECONCILIATION REPORT",
        f"  Ground truth (Claude):  ${report['ground_truth_cost_usd']:.4f}",
        f"  Tracked (Cognitive OS): ${report['tracked_cost_usd']:.4f}",
        f"  Discrepancy:           ${report['discrepancy_usd']:.4f} ({report['discrepancy_pct']}%)",
        f"  Entries analyzed:      {report['entries_analyzed']}",
        f"  Models:                {', '.join(report['models_used'])}",
    ]
    if report["discrepancy_pct"] > 10:
        lines.append("  WARNING: Discrepancy exceeds 10%")
    return "\n".join(lines)
