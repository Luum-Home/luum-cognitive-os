"""Dispatch-time model recommender for agent tasks.

Recommends the optimal model for an agent task based on:
- Task description (classified by keywords)
- Budget remaining (hourly cap from cognitive-os.yaml, default $5)

Used by dispatch-gate.sh (Phase 1) to advise which model to launch with.
Output is human-readable and goes to stderr so the orchestrator can observe it.

Routing table from rules/model-routing.md:
  implementation / apply / tasks  -> sonnet
  propose / design / debugging    -> opus
  archive / docs / format         -> haiku

Budget downgrade thresholds (rules/resource-governance.md):
  < 20% of hourly cap  -> force haiku
  <  5% of hourly cap  -> force haiku + WARN

Python 3.9+ compatible. Author: luum.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Task-type → model routing (mirrors rules/model-routing.md)
# ---------------------------------------------------------------------------

_TASK_MODEL_MAP: Dict[str, str] = {
    "implementation": "sonnet",
    "review": "sonnet",        # verify / review: sonnet per routing table
    "debugging": "opus",
    "documentation": "haiku",
    "archiving": "haiku",
    "propose": "opus",
    "design": "opus",
    "general": "sonnet",       # safe default
}

# Hourly cap default — matches RateLimitConfig.max_cost_per_hour_usd
_DEFAULT_HOURLY_CAP_USD: float = 5.0

# Budget thresholds
_BUDGET_WARN_PCT: float = 5.0     # < 5% remaining  → warn + force haiku
_BUDGET_DOWNGRADE_PCT: float = 20.0  # < 20% remaining → force haiku


# ---------------------------------------------------------------------------
# classify_task_type — reused from lib/record_completion.py
# ---------------------------------------------------------------------------

def classify_task_type(description: str) -> str:
    """Classify task type by keywords in description.

    Returns one of: implementation, review, debugging, documentation,
    archiving, propose, design, general.

    Mirrors lib/record_completion.classify_task_type with additions for
    propose/design so routing can map those to opus.
    """
    desc_lower = description.lower()

    # High-specificity matches first
    if any(kw in desc_lower for kw in ("propose", "proposal")):
        return "propose"
    if any(kw in desc_lower for kw in ("design", "architect")):
        return "design"
    if any(kw in desc_lower for kw in ("debug", "fix", "repair", "error")):
        return "debugging"
    if any(kw in desc_lower for kw in ("archive", "cleanup", "format")):
        return "archiving"
    if any(kw in desc_lower for kw in ("doc", "readme", "document")):
        return "documentation"
    if any(kw in desc_lower for kw in ("review", "verify", "audit", "check")):
        return "review"
    if any(kw in desc_lower for kw in ("implement", "create", "build", "add",
                                        "apply", "task")):
        return "implementation"
    return "general"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _find_config_path() -> Optional[str]:
    """Locate cognitive-os.yaml searching standard locations."""
    candidates: List[str] = []

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get(
        "COGNITIVE_OS_PROJECT_DIR", ""
    )
    if project_dir:
        candidates.append(os.path.join(project_dir, "cognitive-os.yaml"))

    candidates.append("cognitive-os.yaml")
    candidates.append(os.path.join(".cognitive-os", "cognitive-os.yaml"))

    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _read_hourly_cap(config_path: Optional[str] = None) -> float:
    """Read max_cost_per_hour_usd from cognitive-os.yaml.

    Falls back to _DEFAULT_HOURLY_CAP_USD ($5.00) when config is absent or
    the key is not present.
    """
    path = config_path or _find_config_path()
    if path is None:
        return _DEFAULT_HOURLY_CAP_USD

    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"^\s*max_cost_per_hour_usd\s*:\s*([0-9.]+)", line)
                if m:
                    return float(m.group(1))
    except OSError:
        pass

    return _DEFAULT_HOURLY_CAP_USD


def _find_metrics_dir() -> Optional[str]:
    """Locate .cognitive-os/metrics directory."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get(
        "COGNITIVE_OS_PROJECT_DIR", ""
    )
    if project_dir:
        candidate = os.path.join(project_dir, ".cognitive-os", "metrics")
        if os.path.isdir(candidate):
            return candidate

    # CWD-relative fallback
    cwd_candidate = os.path.join(".cognitive-os", "metrics")
    if os.path.isdir(cwd_candidate):
        return cwd_candidate

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_budget_status(
    metrics_dir: Optional[str] = None,
    config_path: Optional[str] = None,
) -> dict:
    """Return current hourly budget status.

    Reads .cognitive-os/metrics/cost-events.jsonl, sums costs from the last
    hour, and compares against max_cost_per_hour_usd from cognitive-os.yaml.

    Returns:
        {
          "hourly_spend": float,
          "hourly_limit": float,
          "remaining": float,
          "pct_used": float,       # 0-100
          "pct_remaining": float,  # 0-100
        }
    """
    hourly_limit = _read_hourly_cap(config_path)

    # Locate cost-events.jsonl
    if metrics_dir is None:
        metrics_dir = _find_metrics_dir()

    cost_file = None
    if metrics_dir:
        candidate = os.path.join(metrics_dir, "cost-events.jsonl")
        if os.path.isfile(candidate):
            cost_file = candidate

    hourly_spend: float = 0.0

    if cost_file:
        now = datetime.now(timezone.utc)
        try:
            with open(cost_file, "r", encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    ts_str = event.get("timestamp", "")
                    if not ts_str:
                        continue

                    try:
                        ts_clean = ts_str.replace("Z", "+00:00")
                        event_dt = datetime.fromisoformat(ts_clean)
                    except (ValueError, TypeError):
                        continue

                    # Make both tz-aware for comparison
                    if event_dt.tzinfo is None:
                        event_dt = event_dt.replace(tzinfo=timezone.utc)

                    age_seconds = (now - event_dt).total_seconds()
                    if age_seconds <= 3600:
                        cost = float(event.get("estimated_cost_usd", 0.0))
                        hourly_spend += cost
        except OSError:
            pass

    remaining = max(0.0, hourly_limit - hourly_spend)
    pct_used = min(100.0, (hourly_spend / hourly_limit * 100) if hourly_limit > 0 else 0.0)
    pct_remaining = max(0.0, 100.0 - pct_used)

    return {
        "hourly_spend": round(hourly_spend, 6),
        "hourly_limit": round(hourly_limit, 6),
        "remaining": round(remaining, 6),
        "pct_used": round(pct_used, 2),
        "pct_remaining": round(pct_remaining, 2),
    }


def recommend_model(
    description: str,
    budget_remaining_usd: Optional[float] = None,
    config_path: Optional[str] = None,
    metrics_dir: Optional[str] = None,
) -> dict:
    """Recommend the optimal model for a task.

    Args:
        description: Task description (free text).
        budget_remaining_usd: If provided, overrides the computed remaining
            budget. Pass None to auto-compute from cost-events.jsonl.
        config_path: Optional path to cognitive-os.yaml.
        metrics_dir: Optional path to .cognitive-os/metrics directory.

    Returns:
        {
          "model": "sonnet" | "opus" | "haiku",
          "reason": str,
          "budget_status": "ok" | "low" | "critical",
          "task_type": str,
          "warning": str | None,   # present only when budget_status != "ok"
        }
    """
    task_type = classify_task_type(description)
    base_model = _TASK_MODEL_MAP.get(task_type, "sonnet")

    # Determine budget context
    if budget_remaining_usd is None:
        budget = get_budget_status(metrics_dir=metrics_dir, config_path=config_path)
        pct_remaining = budget["pct_remaining"]
        remaining_usd = budget["remaining"]
        hourly_limit = budget["hourly_limit"]
    else:
        hourly_limit = _read_hourly_cap(config_path)
        remaining_usd = budget_remaining_usd
        pct_remaining = (
            (remaining_usd / hourly_limit * 100) if hourly_limit > 0 else 100.0
        )

    # Budget downgrade logic (rules/resource-governance.md)
    budget_status = "ok"
    warning: Optional[str] = None
    final_model = base_model

    if pct_remaining < _BUDGET_WARN_PCT:
        # < 5% remaining — force haiku + warn
        final_model = "haiku"
        budget_status = "critical"
        warning = (
            f"Budget critical: only {pct_remaining:.1f}% of hourly cap remaining "
            f"(${remaining_usd:.4f} left). Forced haiku to preserve budget."
        )
    elif pct_remaining < _BUDGET_DOWNGRADE_PCT:
        # < 20% remaining — force haiku
        final_model = "haiku"
        budget_status = "low"
        warning = (
            f"Budget low: {pct_remaining:.1f}% of hourly cap remaining "
            f"(${remaining_usd:.4f} left). Downgraded to haiku."
        )

    reason_parts = [f"{task_type} task"]
    if budget_status != "ok":
        reason_parts.append(f"budget: {pct_remaining:.0f}% remaining")

    result: dict = {
        "model": final_model,
        "reason": ", ".join(reason_parts),
        "budget_status": budget_status,
        "task_type": task_type,
    }
    if warning is not None:
        result["warning"] = warning

    return result


def format_model_advice(recommendation: dict) -> str:
    """Format recommendation as a one-line human-readable string.

    Example:
        "Model: sonnet (implementation task, budget: 45% used)"
    """
    model = recommendation.get("model", "sonnet")
    reason = recommendation.get("reason", "")
    budget_status = recommendation.get("budget_status", "ok")

    budget_note = ""
    if budget_status == "critical":
        budget_note = ", budget: CRITICAL"
    elif budget_status == "low":
        budget_note = ", budget: LOW"

    return f"Model: {model} ({reason}{budget_note})"


# ---------------------------------------------------------------------------
# CLI entry point — outputs advice to stderr for hook consumption
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> None:  # noqa: UP007
    """CLI: recommend_model DESCRIPTION [BUDGET_REMAINING_USD]

    Prints the recommendation as JSON to stdout and a human summary to stderr.
    """
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        print("Usage: dispatch_model_advisor.py DESCRIPTION [BUDGET_USD]", file=sys.stderr)
        sys.exit(1)

    description = args[0]
    budget: Optional[float] = None
    if len(args) >= 2:
        try:
            budget = float(args[1])
        except ValueError:
            print(f"Warning: invalid budget value '{args[1]}', ignoring", file=sys.stderr)

    rec = recommend_model(description, budget_remaining_usd=budget)
    advice = format_model_advice(rec)

    print(json.dumps(rec))
    print(advice, file=sys.stderr)


if __name__ == "__main__":
    main()
