# SCOPE: os-only
"""Budget accounting for COS-native goal loop — all four dimensions (OD-002).

Implements REQ-008. All four budget dimensions are enforced in MVP:

  1. max_turns         — turn counter stored in GoalState.turns_used
  2. wall_clock_minutes — derived from time.time() - GoalState.started_at_epoch
  3. max_tokens         — cumulative tokens_in + tokens_out from llm-dispatch.jsonl
  4. max_cost_usd       — cumulative cost_usd from llm-dispatch.jsonl

The JSONL file is read via lib.dispatch._metrics_path() and degrades gracefully
when the file is absent (returns zeros, does not raise).

JSONL record schema (per lib/dispatch.py):
  ts           : ISO-8601 datetime string (Z-suffix or offset)
  dispatch_id  : str
  tokens_in    : int
  tokens_out   : int
  cost_usd     : float
  (other fields ignored)
"""

from __future__ import annotations

import datetime
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lib.goal_state import GoalState


# ---------------------------------------------------------------------------
# Dispatch metrics reader
# ---------------------------------------------------------------------------


def _goal_dispatch_totals(
    goal_created_at: str,
    project_dir: Path | None = None,
) -> tuple[int, float]:
    """Return (total_tokens, total_cost_usd) for dispatches since goal creation.

    Reads .cognitive-os/metrics/llm-dispatch.jsonl via lib.dispatch._metrics_path().
    Returns (0, 0.0) gracefully when the file is absent or unreadable.

    Args:
        goal_created_at: ISO-8601 string (the goal's created_at timestamp).
            Only dispatch records with ts >= this value are counted.
        project_dir: Optional override for project root resolution.
    """
    try:
        from lib.dispatch import _metrics_path
        path = _metrics_path(project_dir)
    except Exception:  # noqa: BLE001
        return 0, 0.0

    total_tokens: int = 0
    total_cost: float = 0.0

    if not path.exists():
        return total_tokens, total_cost

    try:
        cutoff = datetime.datetime.fromisoformat(
            goal_created_at.replace("Z", "+00:00")
        )
    except (ValueError, AttributeError):
        # Unparseable timestamp — count all records conservatively
        cutoff = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    ts_raw = rec.get("ts", "")
                    rec_ts = datetime.datetime.fromisoformat(
                        ts_raw.replace("Z", "+00:00")
                    )
                    # Make cutoff timezone-aware if rec_ts is
                    cmp_cutoff = cutoff
                    if rec_ts.tzinfo is not None and cutoff.tzinfo is None:
                        cmp_cutoff = cutoff.replace(tzinfo=datetime.timezone.utc)
                    elif rec_ts.tzinfo is None and cmp_cutoff.tzinfo is not None:
                        rec_ts = rec_ts.replace(tzinfo=datetime.timezone.utc)
                    if rec_ts >= cmp_cutoff:
                        total_tokens += int(rec.get("tokens_in", 0)) + int(
                            rec.get("tokens_out", 0)
                        )
                        total_cost += float(rec.get("cost_usd", 0.0))
                except Exception:  # noqa: BLE001
                    continue
    except OSError:
        pass

    return total_tokens, total_cost


# ---------------------------------------------------------------------------
# Budget exhaustion check result
# ---------------------------------------------------------------------------


@dataclass
class BudgetCheckResult:
    """Outcome of checking all four budget dimensions."""

    exhausted: bool
    """True when at least one dimension is over its limit."""

    dimension: str
    """Which dimension triggered exhaustion (empty string if none)."""

    reason: str
    """Human-readable explanation."""

    turns_used: int = 0
    wall_minutes_used: float = 0.0
    tokens_used: int = 0
    cost_used: float = 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_budget(
    goal: "GoalState",
    project_dir: Path | None = None,
) -> BudgetCheckResult:
    """Check all four budget dimensions for the given goal.

    Dimensions are evaluated in the order specified in the design:
      1. max_turns (cheapest — no I/O)
      2. wall_clock_minutes (cheap — time.time())
      3. max_tokens (requires reading llm-dispatch.jsonl)
      4. max_cost_usd (same file, combined read)

    Returns a BudgetCheckResult. If any dimension is exhausted, ``exhausted``
    is True and ``dimension``/``reason`` name the first breach.

    Gracefully handles absent dispatch metrics file (returns zeros for 3 & 4).
    """
    turns_used = goal.turns_used
    wall_minutes_used = (time.time() - goal.started_at_epoch) / 60.0

    # Dimensions 3 & 4 share a single file read
    tokens_used: int = 0
    cost_used: float = 0.0
    if goal.max_tokens is not None or goal.max_cost_usd is not None:
        tokens_used, cost_used = _goal_dispatch_totals(goal.created_at, project_dir)

    # --- Dimension 1: max_turns ---
    if goal.max_turns is not None and turns_used >= goal.max_turns:
        return BudgetCheckResult(
            exhausted=True,
            dimension="max_turns",
            reason=(
                f"Turn budget exhausted: {turns_used}/{goal.max_turns} turns used."
            ),
            turns_used=turns_used,
            wall_minutes_used=wall_minutes_used,
            tokens_used=tokens_used,
            cost_used=cost_used,
        )

    # --- Dimension 2: wall_clock_minutes ---
    if goal.max_minutes is not None and wall_minutes_used >= goal.max_minutes:
        return BudgetCheckResult(
            exhausted=True,
            dimension="wall_clock_minutes",
            reason=(
                f"Wall-clock budget exhausted: {wall_minutes_used:.1f}/{goal.max_minutes} "
                "minutes elapsed."
            ),
            turns_used=turns_used,
            wall_minutes_used=wall_minutes_used,
            tokens_used=tokens_used,
            cost_used=cost_used,
        )

    # --- Dimension 3: max_tokens ---
    if goal.max_tokens is not None and tokens_used >= goal.max_tokens:
        return BudgetCheckResult(
            exhausted=True,
            dimension="max_tokens",
            reason=(
                f"Token budget exhausted: {tokens_used}/{goal.max_tokens} tokens used."
            ),
            turns_used=turns_used,
            wall_minutes_used=wall_minutes_used,
            tokens_used=tokens_used,
            cost_used=cost_used,
        )

    # --- Dimension 4: max_cost_usd ---
    if goal.max_cost_usd is not None and cost_used >= goal.max_cost_usd:
        return BudgetCheckResult(
            exhausted=True,
            dimension="max_cost_usd",
            reason=(
                f"Cost budget exhausted: ${cost_used:.4f}/${goal.max_cost_usd:.4f} spent."
            ),
            turns_used=turns_used,
            wall_minutes_used=wall_minutes_used,
            tokens_used=tokens_used,
            cost_used=cost_used,
        )

    return BudgetCheckResult(
        exhausted=False,
        dimension="",
        reason="Budget within limits.",
        turns_used=turns_used,
        wall_minutes_used=wall_minutes_used,
        tokens_used=tokens_used,
        cost_used=cost_used,
    )
