# scope: both
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


def _read_monthly_budget(config_path: Optional[str] = None) -> float:
    """Read monthly_limit_usd from cognitive-os.yaml.

    Falls back to 0.0 (unlimited) when config is absent or key is not present.
    """
    path = config_path or _find_config_path()
    if path is None:
        return 0.0

    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"^\s*monthly_limit_usd\s*:\s*([0-9.]+)", line)
                if m:
                    return float(m.group(1))
    except OSError:
        pass

    return 0.0


def get_monthly_budget_status(
    metrics_dir: Optional[str] = None,
    config_path: Optional[str] = None,
) -> dict:
    """Return current monthly budget status.

    Reads .cognitive-os/metrics/cost-events.jsonl, sums costs from the current
    calendar month, and compares against monthly_limit_usd from cognitive-os.yaml.

    Returns:
        {
          "monthly_spend": float,
          "monthly_limit": float,
          "remaining": float,
          "pct_used": float,       # 0-100
          "pct_remaining": float,  # 0-100
          "limited": bool,         # False when monthly_limit == 0 (no limit set)
        }
    """
    monthly_limit = _read_monthly_budget(config_path)

    if metrics_dir is None:
        metrics_dir = _find_metrics_dir()

    cost_file = None
    if metrics_dir:
        candidate = os.path.join(metrics_dir, "cost-events.jsonl")
        if os.path.isfile(candidate):
            cost_file = candidate

    monthly_spend: float = 0.0

    if cost_file:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
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

                    if event_dt.tzinfo is None:
                        event_dt = event_dt.replace(tzinfo=timezone.utc)

                    if event_dt >= month_start:
                        cost = float(event.get("estimated_cost_usd", 0.0))
                        monthly_spend += cost
        except OSError:
            pass

    if monthly_limit <= 0.0:
        # No monthly limit configured
        return {
            "monthly_spend": round(monthly_spend, 6),
            "monthly_limit": 0.0,
            "remaining": float("inf"),
            "pct_used": 0.0,
            "pct_remaining": 100.0,
            "limited": False,
        }

    remaining = max(0.0, monthly_limit - monthly_spend)
    pct_used = min(100.0, (monthly_spend / monthly_limit * 100))
    pct_remaining = max(0.0, 100.0 - pct_used)

    return {
        "monthly_spend": round(monthly_spend, 6),
        "monthly_limit": round(monthly_limit, 6),
        "remaining": round(remaining, 6),
        "pct_used": round(pct_used, 2),
        "pct_remaining": round(pct_remaining, 2),
        "limited": True,
    }


def recommend_model(
    description: str,
    budget_remaining_usd: Optional[float] = None,
    config_path: Optional[str] = None,
    metrics_dir: Optional[str] = None,
    skill_name: Optional[str] = None,
) -> dict:
    """Recommend the optimal model for a task.

    Args:
        description: Task description (free text).
        budget_remaining_usd: If provided, overrides the computed remaining
            budget. Pass None to auto-compute from cost-events.jsonl.
        config_path: Optional path to cognitive-os.yaml.
        metrics_dir: Optional path to .cognitive-os/metrics directory.
        skill_name: Optional skill name for consequence override lookup.
            If provided and the skill is DISABLED, result["disabled"] = True.

    Returns:
        {
          "model": "sonnet" | "opus" | "haiku",
          "reason": str,
          "budget_status": "ok" | "low" | "critical",
          "task_type": str,
          "confidence": float,     # 0.0-1.0
          "disabled": bool,        # True when skill is DISABLED by consequence engine
          "warning": str | None,   # present only when budget_status != "ok"
        }
    """
    task_type = classify_task_type(description)
    base_model = _TASK_MODEL_MAP.get(task_type, "sonnet")

    # ── Step 1: Consequence override (skill performance history) ─────────────
    consequence_model: Optional[str] = None
    is_disabled = False
    consequence_reason: Optional[str] = None

    if skill_name is not None:
        try:
            from lib.model_router import get_consequence_override
            override = get_consequence_override(skill_name, metrics_dir=metrics_dir)
            if override is None:
                # DISABLED
                is_disabled = True
                consequence_reason = f"skill '{skill_name}' is DISABLED by consequence engine"
            elif override != "no-override":
                consequence_model = override
                consequence_reason = f"consequence override for '{skill_name}'"
        except Exception:
            pass  # Consequence engine unavailable; proceed without override

    # ── Step 2: Hourly budget status ─────────────────────────────────────────
    if budget_remaining_usd is None:
        budget = get_budget_status(metrics_dir=metrics_dir, config_path=config_path)
        hourly_pct_remaining = budget["pct_remaining"]
        remaining_usd = budget["remaining"]
        hourly_limit = budget["hourly_limit"]
    else:
        hourly_limit = _read_hourly_cap(config_path)
        remaining_usd = budget_remaining_usd
        hourly_pct_remaining = (
            (remaining_usd / hourly_limit * 100) if hourly_limit > 0 else 100.0
        )

    # ── Step 3: Monthly budget downgrade chain (resource-governance.md) ──────
    monthly = get_monthly_budget_status(metrics_dir=metrics_dir, config_path=config_path)
    monthly_pct_used = monthly["pct_used"] if monthly["limited"] else 0.0

    # ── Step 4: Determine final model ────────────────────────────────────────
    budget_status = "ok"
    warning: Optional[str] = None

    # Monthly budget downgrade takes precedence over task-type routing
    if monthly["limited"] and monthly_pct_used >= 95.0:
        base_model = "haiku"
        budget_status = "critical"
        warning = (
            f"Monthly budget critical: {monthly_pct_used:.0f}% used "
            f"(${monthly['monthly_spend']:.2f} of ${monthly['monthly_limit']:.2f}). "
            f"Forced haiku."
        )
    elif monthly["limited"] and monthly_pct_used >= 80.0:
        # >80% monthly: force sonnet (except already-cheaper models)
        if base_model == "opus":
            base_model = "sonnet"
        budget_status = "low"
        warning = (
            f"Monthly budget low: {monthly_pct_used:.0f}% used. "
            f"Downgraded opus→sonnet."
        )
    elif hourly_pct_remaining < _BUDGET_WARN_PCT:
        # < 5% hourly remaining — force haiku + warn
        base_model = "haiku"
        budget_status = "critical"
        warning = (
            f"Budget critical: only {hourly_pct_remaining:.1f}% of hourly cap remaining "
            f"(${remaining_usd:.4f} left). Forced haiku to preserve budget."
        )
    elif hourly_pct_remaining < _BUDGET_DOWNGRADE_PCT:
        # < 20% hourly remaining — force haiku
        base_model = "haiku"
        budget_status = "low"
        warning = (
            f"Budget low: {hourly_pct_remaining:.1f}% of hourly cap remaining "
            f"(${remaining_usd:.4f} left). Downgraded to haiku."
        )

    # Apply consequence override on top of budget decisions
    # Consequence can only downgrade, not upgrade past the budget-determined model
    if consequence_model is not None and not is_disabled:
        # If consequence says downgrade, apply it (but not past what budget already chose)
        _model_rank = {"opus": 3, "sonnet": 2, "haiku": 1}
        consequence_rank = _model_rank.get(consequence_model, 2)
        base_rank = _model_rank.get(base_model, 2)
        if consequence_rank < base_rank:
            base_model = consequence_model

    final_model = base_model

    # ── Confidence ───────────────────────────────────────────────────────────
    confidence = 1.0
    if budget_status != "ok":
        confidence -= 0.1
    if consequence_model is not None:
        confidence -= 0.05  # slight uncertainty when consequence overrides apply
    confidence = max(0.5, round(confidence, 2))

    # ── Reason string ────────────────────────────────────────────────────────
    reason_parts = [f"{task_type} task"]
    if budget_status != "ok":
        if monthly["limited"] and monthly_pct_used >= 80.0:
            reason_parts.append(f"monthly budget: {monthly_pct_used:.0f}% used")
        else:
            reason_parts.append(f"hourly budget: {hourly_pct_remaining:.0f}% remaining")
    if consequence_reason:
        reason_parts.append(consequence_reason)

    result: dict = {
        "model": final_model,
        "reason": ", ".join(reason_parts),
        "budget_status": budget_status,
        "task_type": task_type,
        "confidence": confidence,
        "disabled": is_disabled,
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


def format_model_directive(recommendation: dict) -> str:
    """Format recommendation as a structured MODEL_DIRECTIVE marker.

    The orchestrator MUST use the specified model when this directive is present.
    Returns empty string if the recommendation is advisory-only (confidence < threshold).

    Examples:
        "MODEL_DIRECTIVE: sonnet"
        "MODEL_DISABLED: skill is DISABLED by consequence engine"
    """
    if recommendation.get("disabled", False):
        reason = recommendation.get("reason", "consequence engine")
        return f"MODEL_DISABLED: {reason}"

    model = recommendation.get("model", "sonnet")
    confidence = recommendation.get("confidence", 1.0)

    # Only emit a directive when we have enough confidence to mandate it
    if confidence >= 0.7:
        return f"MODEL_DIRECTIVE: {model}"

    # Low confidence → advisory only (no directive)
    return f"MODEL_ADVICE: {model}"


# ---------------------------------------------------------------------------
# CLI entry point — outputs advice to stderr for hook consumption
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> None:  # noqa: UP007
    """CLI: recommend_model DESCRIPTION [BUDGET_REMAINING_USD] [SKILL_NAME]

    Prints the recommendation as JSON to stdout and a human summary to stderr.
    """
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        print("Usage: dispatch_model_advisor.py DESCRIPTION [BUDGET_USD] [SKILL_NAME]", file=sys.stderr)
        sys.exit(1)

    description = args[0]
    budget: Optional[float] = None
    skill: Optional[str] = None

    if len(args) >= 2:
        try:
            budget = float(args[1])
        except ValueError:
            print(f"Warning: invalid budget value '{args[1]}', ignoring", file=sys.stderr)

    if len(args) >= 3:
        skill = args[2]

    rec = recommend_model(description, budget_remaining_usd=budget, skill_name=skill)
    advice = format_model_advice(rec)

    print(json.dumps(rec))
    print(advice, file=sys.stderr)


if __name__ == "__main__":
    main()
