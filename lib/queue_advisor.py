"""Queue Advisor — dynamic dispatch prioritizer for the agent queue.

Reorders the dispatch queue based on runtime state (budget, context usage,
task dependencies, staleness) using weighted heuristic scoring.

Public API:
    from lib.queue_advisor import QueueAdvisor

    advisor = QueueAdvisor()
    reordered = advisor.advise(queue_items)
    print(advisor.format_advice(reordered))

v1: Algorithmic scoring (5 weighted factors, zero API cost).
v2: Haiku-powered semantic scoring (~$0.003/call) for better dependency
    inference and task description understanding. Activated automatically
    when queue has 5+ items (mode="auto") or explicitly with mode="llm".

Python 3.9+ compatible. No external dependencies. Author: luum.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from lib.config_loader import find_config_path as _cl_find_config_path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_COGNITIVE_OS_DIR = ".cognitive-os"
_DEFAULT_COST_EVENTS = os.path.join(_COGNITIVE_OS_DIR, "metrics", "cost-events.jsonl")
_DEFAULT_TASKS_PATH = os.path.join(_COGNITIVE_OS_DIR, "tasks", "active-tasks.json")
_DEFAULT_CONFIG_PATH = "cognitive-os.yaml"

# Scoring weights — must sum to 1.0
_WEIGHT_DEPENDENCY = 0.30
_WEIGHT_BUDGET = 0.25
_WEIGHT_CONTEXT = 0.20
_WEIGHT_STALENESS = 0.15
_WEIGHT_MODEL_EFFICIENCY = 0.10

# Budget threshold above which cheap-model preference kicks in
_BUDGET_PRESSURE_THRESHOLD = 0.80

# Context usage threshold above which small-task preference kicks in
_CONTEXT_PRESSURE_THRESHOLD = 0.70

# Approximate tokens-per-char ratio for description length estimation
_TOKENS_PER_CHAR = 0.25

# Model efficiency scores (higher = preferred when resources are tight)
_MODEL_EFFICIENCY: Dict[str, int] = {
    "haiku": 100,
    "sonnet": 60,
    "opus": 30,
    # Aliases
    "claude-haiku-3.5": 100,
    "claude-sonnet-4": 60,
    "claude-opus-4-6": 30,
}

# Model cost tiers (for budget score)
_MODEL_BUDGET_TIER: Dict[str, str] = {
    "haiku": "cheap",
    "sonnet": "mid",
    "opus": "expensive",
    "claude-haiku-3.5": "cheap",
    "claude-sonnet-4": "mid",
    "claude-opus-4-6": "expensive",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_daily_limit(project_dir: str) -> float:
    """Parse resources.budget.daily_alert_usd from cognitive-os.yaml."""
    # Search project_dir first, then fall back to canonical env-var / cwd search.
    _project_candidates = [
        os.path.join(project_dir, "cognitive-os.yaml"),
        os.path.join(project_dir, _COGNITIVE_OS_DIR, "cognitive-os.yaml"),
    ]
    path: Optional[str] = next(
        (p for p in _project_candidates if os.path.isfile(p)), None
    ) or _cl_find_config_path()
    if not path:
        return 10.0  # sensible default

    try:
        with open(path) as fh:
            content = fh.read()
        # Look for daily_alert_usd key
        m = re.search(r"daily_alert_usd:\s*([\d.]+)", content)
        if m:
            return float(m.group(1))
    except (OSError, ValueError):
        pass
    return 10.0


def _read_daily_spend(project_dir: str) -> float:
    """Sum today's spend from cost-events.jsonl."""
    path = os.path.join(project_dir, _DEFAULT_COST_EVENTS)
    if not os.path.isfile(path):
        return 0.0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = 0.0
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = entry.get("timestamp", "")
                    if ts.startswith(today):
                        total += float(entry.get("estimated_cost_usd", 0.0))
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
    except OSError:
        pass
    return total


def _load_active_tasks(project_dir: str) -> List[Dict[str, Any]]:
    """Load tasks from active-tasks.json."""
    path = os.path.join(project_dir, _DEFAULT_TASKS_PATH)
    if not os.path.isfile(path):
        return []
    try:
        with open(path) as fh:
            data = json.load(fh)
        return data.get("tasks", []) if isinstance(data, dict) else []
    except (json.JSONDecodeError, OSError):
        return []


def _minutes_since(iso_timestamp: str) -> float:
    """Return minutes elapsed since an ISO-8601 UTC timestamp."""
    if not iso_timestamp:
        return 0.0
    try:
        # Accept both 'Z' suffix and '+00:00'
        ts = iso_timestamp.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        elapsed = datetime.now(timezone.utc) - dt
        return elapsed.total_seconds() / 60.0
    except (ValueError, OverflowError):
        return 0.0


def _estimate_tokens(item: Dict[str, Any]) -> int:
    """Rough token estimate from description length."""
    description = item.get("description", item.get("prompt", ""))
    return max(100, int(len(description) * _TOKENS_PER_CHAR * 100))


# ---------------------------------------------------------------------------
# QueueAdvisor
# ---------------------------------------------------------------------------


class QueueAdvisor:
    """Dynamic queue prioritizer based on runtime state.

    Scores each queue item across 5 weighted dimensions and returns the
    items reordered by descending advisory score. If scoring fails for any
    reason, the original order is preserved (graceful fallback).

    Args:
        project_dir: Root directory of the project (defaults to '.').
    """

    def __init__(self, project_dir: str = ".") -> None:
        self.project_dir = project_dir
        self._state: Optional[Dict[str, Any]] = None  # lazy-loaded

    # ------------------------------------------------------------------ #
    # Runtime state                                                        #
    # ------------------------------------------------------------------ #

    def get_runtime_state(self) -> Dict[str, Any]:
        """Collect runtime metrics used for scoring.

        Returns:
            {
                budget_used_pct:    float 0.0–1.0  (daily spend / limit)
                context_usage_pct:  float 0.0–1.0  (estimated, 0 if unknown)
                completed_task_ids: set[str]        (IDs of completed tasks)
                active_count:       int             (in_progress task count)
                dependency_map:     dict[str,list]  (task_id -> depends_on)
            }
        """
        # Budget
        daily_limit = _read_daily_limit(self.project_dir)
        daily_spend = _read_daily_spend(self.project_dir)
        budget_used_pct = (daily_spend / daily_limit) if daily_limit > 0 else 0.0
        budget_used_pct = min(1.0, budget_used_pct)

        # Tasks
        tasks = _load_active_tasks(self.project_dir)
        completed_ids = {
            t.get("id", "")
            for t in tasks
            if t.get("status") in ("completed", "done")
        }
        active_count = sum(
            1 for t in tasks if t.get("status") == "in_progress"
        )

        # Build dependency map: task_id -> list of task_ids it depends on
        dependency_map: Dict[str, List[str]] = {}
        for t in tasks:
            tid = t.get("id", "")
            if tid:
                deps = t.get("depends_on", t.get("dependencies", []))
                if isinstance(deps, list):
                    dependency_map[tid] = deps

        # Context usage — attempt to read from metrics if available
        context_usage_pct = self._estimate_context_usage()

        return {
            "budget_used_pct": budget_used_pct,
            "context_usage_pct": context_usage_pct,
            "completed_task_ids": completed_ids,
            "active_count": active_count,
            "dependency_map": dependency_map,
        }

    def _estimate_context_usage(self) -> float:
        """Try to read context usage from context-usage metrics."""
        path = os.path.join(
            self.project_dir, _COGNITIVE_OS_DIR, "metrics", "context-usage.jsonl"
        )
        if not os.path.isfile(path):
            return 0.0
        try:
            # Read last entry
            last_line = ""
            with open(path) as fh:
                for line in fh:
                    if line.strip():
                        last_line = line.strip()
            if not last_line:
                return 0.0
            entry = json.loads(last_line)
            # Prefer explicit field, else infer from token counts
            if "context_usage_pct" in entry:
                return min(1.0, float(entry["context_usage_pct"]) / 100.0)
            total_overhead = entry.get("total_overhead", 0)
            max_context = 200_000  # conservative estimate
            if total_overhead:
                return min(1.0, total_overhead / max_context)
        except (json.JSONDecodeError, ValueError, OSError):
            pass
        return 0.0

    # ------------------------------------------------------------------ #
    # Scoring                                                              #
    # ------------------------------------------------------------------ #

    def score_item(
        self, item: Dict[str, Any], state: Dict[str, Any]
    ) -> Tuple[float, str]:
        """Score a single queue item from 0–100.

        Args:
            item:  A queue item dict (must have at least 'id', 'model', 'enqueued_at').
            state: Runtime state from get_runtime_state().

        Returns:
            (score, reason) where score is 0.0–100.0 and reason is a short string.
        """
        reasons: List[str] = []

        dep_score = self._score_dependency(item, state)
        budget_score = self._score_budget(item, state)
        context_score = self._score_context(item, state)
        staleness_score = self._score_staleness(item)
        efficiency_score = self._score_model_efficiency(item)

        total = (
            dep_score * _WEIGHT_DEPENDENCY
            + budget_score * _WEIGHT_BUDGET
            + context_score * _WEIGHT_CONTEXT
            + staleness_score * _WEIGHT_STALENESS
            + efficiency_score * _WEIGHT_MODEL_EFFICIENCY
        )

        # Build reason string
        if dep_score >= 75:
            reasons.append("unblocks dependents")
        if dep_score == 0 and state.get("dependency_map"):
            item_deps = self._get_item_deps(item, state)
            if item_deps:
                reasons.append("blocked by unmet deps")
        if budget_score >= 75 and state["budget_used_pct"] > _BUDGET_PRESSURE_THRESHOLD:
            reasons.append("cheap under budget pressure")
        if staleness_score >= 50:
            mins = _minutes_since(item.get("enqueued_at", ""))
            if mins >= 5:
                reasons.append(f"waited {int(mins)}m")
        if efficiency_score >= 75:
            reasons.append(f"efficient model ({item.get('model', '?')})")

        reason = "; ".join(reasons) if reasons else "standard priority"
        return round(total, 2), reason

    def _get_item_deps(
        self, item: Dict[str, Any], state: Dict[str, Any]
    ) -> List[str]:
        """Return unmet dependencies for this queue item."""
        item_id = item.get("id", "")
        dep_map = state.get("dependency_map", {})
        completed = state.get("completed_task_ids", set())
        deps = dep_map.get(item_id, [])
        return [d for d in deps if d not in completed]

    def _score_dependency(
        self, item: Dict[str, Any], state: Dict[str, Any]
    ) -> float:
        """Score 0–100 based on how many tasks this item unblocks.

        Also penalises items whose own dependencies are not yet completed.
        """
        item_id = item.get("id", "")
        dep_map = state.get("dependency_map", {})
        completed = state.get("completed_task_ids", set())

        # Check if this item has unmet dependencies (can't run yet)
        own_deps = dep_map.get(item_id, [])
        unmet = [d for d in own_deps if d not in completed]
        if unmet:
            return 0.0

        # Count how many other tasks depend on this item
        unblocked_count = sum(
            1
            for tid, deps in dep_map.items()
            if item_id in deps and tid not in completed
        )
        return min(100.0, unblocked_count * 25.0)

    def _score_budget(
        self, item: Dict[str, Any], state: Dict[str, Any]
    ) -> float:
        """Score 0–100 preferring cheaper models when budget is tight."""
        budget_pct = state.get("budget_used_pct", 0.0)
        model = item.get("model", "sonnet").lower()
        tier = _MODEL_BUDGET_TIER.get(model, "mid")

        if budget_pct > _BUDGET_PRESSURE_THRESHOLD:
            # Prefer cheap models under budget pressure
            if tier == "cheap":
                return 100.0
            if tier == "mid":
                return 50.0
            return 0.0  # expensive models deprioritised
        else:
            # No budget pressure — neutral score for all
            return 50.0

    def _score_context(
        self, item: Dict[str, Any], state: Dict[str, Any]
    ) -> float:
        """Score 0–100 preferring tasks with smaller context footprint when context is high."""
        context_pct = state.get("context_usage_pct", 0.0)
        est_tokens = _estimate_tokens(item)

        if context_pct > _CONTEXT_PRESSURE_THRESHOLD:
            # Prefer smaller tasks when context is crowded
            # Score decreases as estimated tokens increase
            # 100 tokens → 100, 1000 tokens → ~90, 5000 → ~50, 10000+ → ~0
            score = max(0.0, 100.0 - (est_tokens / 100.0))
            return min(100.0, score)
        else:
            return 50.0  # neutral when context is not a concern

    def _score_staleness(self, item: Dict[str, Any]) -> float:
        """Score 0–100 boosting older queue items."""
        mins = _minutes_since(item.get("enqueued_at", ""))
        # Every minute waiting adds 5 points, capped at 100
        return min(100.0, mins * 5.0)

    def _score_model_efficiency(self, item: Dict[str, Any]) -> float:
        """Score 0–100 always slightly preferring cheaper models."""
        model = item.get("model", "sonnet").lower()
        return float(_MODEL_EFFICIENCY.get(model, 60))

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def _advise_algorithmic(
        self, queue_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """v1 algorithmic scoring — pure Python, zero API cost.

        Each returned item gains two extra fields:
          - advisor_score  (float 0–100)
          - advisor_reason (str)

        Items with unmet dependencies get score 0 and are pushed to the
        back. Within equal advisory scores, original priority + FIFO order
        is preserved as a tiebreaker.

        Args:
            queue_items: List of queue item dicts.

        Returns:
            Reordered list with advisor_score and advisor_reason fields added.
            Returns a copy — does not mutate input items.
        """
        if not queue_items:
            return []

        try:
            state = self.get_runtime_state()
            scored: List[Dict[str, Any]] = []
            for idx, raw_item in enumerate(queue_items):
                item = dict(raw_item)  # shallow copy
                score, reason = self.score_item(item, state)
                item["advisor_score"] = score
                item["advisor_reason"] = reason
                item["_original_idx"] = idx  # for stable tiebreaking
                scored.append(item)

            # Sort: descending advisor_score, then ascending original priority,
            # then ascending original index (FIFO within same priority+score).
            scored.sort(
                key=lambda x: (
                    -x["advisor_score"],
                    x.get("priority", 5),
                    x["_original_idx"],
                )
            )

            # Clean up internal field
            for item in scored:
                item.pop("_original_idx", None)

            return scored

        except Exception:
            # Graceful fallback: return originals unchanged
            return [dict(item) for item in queue_items]

    def _call_haiku(self, prompt: str) -> Optional[str]:
        """Call haiku via claude CLI. Returns response text or None on failure.

        Args:
            prompt: The full prompt text to send to haiku.

        Returns:
            Response text from claude, or None if the call fails for any reason
            (CLI not available, non-zero exit, timeout, exception).
        """
        try:
            result = subprocess.run(
                ["claude", "-m", "haiku", "-p", prompt, "--no-input"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    def advise_with_llm(
        self,
        queue_items: List[Dict[str, Any]],
        model: str = "haiku",
    ) -> List[Dict[str, Any]]:
        """Use an LLM to semantically reorder the queue (v2 mode).

        Sends a structured prompt to haiku with:
        - Current queue items (id, description, model, priority, enqueued_at)
        - Runtime state (budget %, context %, completed tasks, active agents)
        - Algorithmic scores from v1 (as a starting point)

        The LLM can override algorithmic ordering when it detects:
        - Semantic dependencies not visible in task metadata
        - Tasks that should be batched together
        - Tasks that conflict (edit same files)

        Falls back to v1 algorithmic scoring if the LLM call fails, returns
        unparseable output, or references unknown task IDs.

        Args:
            queue_items: List of queue item dicts.
            model: Model short-name to use (currently only "haiku" is used via
                   the claude CLI; the parameter is kept for future flexibility).

        Returns:
            Reordered list with advisor_score and advisor_reason fields added.
        """
        if not queue_items:
            return []

        # Compute v1 scores first — they serve as the algorithmic baseline
        # and are embedded in the prompt so the LLM can build on them.
        v1_result = self._advise_algorithmic(queue_items)
        algorithmic_scores: Dict[str, float] = {
            item.get("id", str(i)): item.get("advisor_score", 0.0)
            for i, item in enumerate(v1_result)
        }

        # Gather runtime state for the prompt
        try:
            state = self.get_runtime_state()
        except Exception:
            return v1_result

        budget_pct = round(state.get("budget_used_pct", 0.0) * 100, 1)
        context_pct = round(state.get("context_usage_pct", 0.0) * 100, 1)
        active_count = state.get("active_count", 0)
        completed_ids = list(state.get("completed_task_ids", set()))

        # Build the task list for the prompt
        task_summaries = []
        for item in v1_result:
            task_summaries.append(
                {
                    "id": item.get("id", ""),
                    "description": (item.get("description") or item.get("prompt", ""))[:120],
                    "model": item.get("model", "sonnet"),
                    "priority": item.get("priority", 5),
                    "algorithmic_score": item.get("advisor_score", 0.0),
                }
            )

        prompt = (
            "You are a task queue prioritizer. Given these pending tasks and runtime state, "
            "reorder them optimally.\n\n"
            f"PENDING TASKS:\n{json.dumps(task_summaries, indent=2)}\n\n"
            "RUNTIME STATE:\n"
            f"- Budget used: {budget_pct}%\n"
            f"- Context usage: {context_pct}%\n"
            f"- Completed this session: {completed_ids}\n"
            f"- Active agents: {active_count}\n\n"
            f"ALGORITHMIC SCORES (v1 baseline):\n"
            f"{json.dumps(algorithmic_scores, indent=2)}\n\n"
            "OUTPUT FORMAT (JSON only, no explanation):\n"
            '[{"id": "task-1", "reason": "unblocks 3 others"}, '
            '{"id": "task-3", "reason": "cheap, clears queue"}]\n\n'
            "Rules:\n"
            "- Tasks editing the same files should not run in parallel (flag conflicts)\n"
            "- Cheaper tasks first when budget is tight\n"
            "- Tasks that unblock others take priority\n"
            "- Batch related tasks together if possible"
        )

        response = self._call_haiku(prompt)
        if not response:
            return v1_result

        # Parse LLM response — expect a JSON array of {id, reason} objects
        reordered = self._parse_llm_response(response, v1_result)
        return reordered if reordered is not None else v1_result

    def _parse_llm_response(
        self,
        response: str,
        v1_fallback: List[Dict[str, Any]],
    ) -> Optional[List[Dict[str, Any]]]:
        """Parse LLM JSON response and produce a reordered item list.

        Returns None if parsing fails or the response is structurally invalid,
        so the caller can fall back to v1.

        Args:
            response:    Raw text from the LLM.
            v1_fallback: The v1-scored items, used to look up full item dicts
                         by ID and as the basis for advisor_score values.

        Returns:
            Reordered list of item dicts (with advisor_score/advisor_reason) or
            None on parse failure.
        """
        # Build lookup: id -> item dict from v1 results
        item_by_id: Dict[str, Dict[str, Any]] = {}
        for item in v1_fallback:
            item_id = item.get("id", "")
            if item_id:
                item_by_id[item_id] = item

        # Extract JSON array from response — the LLM might wrap it in markdown
        json_text = response
        # Strip code fences if present
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if fence_match:
            json_text = fence_match.group(1).strip()
        else:
            # Try to find a bare JSON array
            array_match = re.search(r"\[[\s\S]*\]", response)
            if array_match:
                json_text = array_match.group(0)

        try:
            parsed = json.loads(json_text)
        except (json.JSONDecodeError, ValueError):
            return None

        if not isinstance(parsed, list):
            return None

        reordered: List[Dict[str, Any]] = []
        seen_ids: set = set()

        for rank, entry in enumerate(parsed):
            if not isinstance(entry, dict):
                continue
            item_id = entry.get("id", "")
            if not item_id or item_id not in item_by_id:
                # Unknown or missing ID — abort and fall back
                return None
            if item_id in seen_ids:
                continue  # deduplicate
            seen_ids.add(item_id)

            item = dict(item_by_id[item_id])
            # Assign a synthetic score based on LLM rank (100 for first, descending)
            item["advisor_score"] = max(0.0, round(100.0 - rank * (100.0 / len(parsed)), 2))
            reason = entry.get("reason", "llm-reordered")
            item["advisor_reason"] = f"[llm] {reason}"
            reordered.append(item)

        # Append any items the LLM omitted (shouldn't happen, but be safe)
        for item in v1_fallback:
            if item.get("id", "") not in seen_ids:
                reordered.append(dict(item))

        return reordered if reordered else None

    def advise(
        self,
        queue_items: List[Dict[str, Any]],
        mode: str = "auto",
    ) -> List[Dict[str, Any]]:
        """Reorder queue items by advisory score (highest first).

        Selects between algorithmic (v1) and LLM-powered (v2) scoring based
        on *mode* and queue size.

        Each returned item gains two extra fields:
          - advisor_score  (float 0–100)
          - advisor_reason (str)

        Args:
            queue_items: List of queue item dicts (from QueueDrainer.get_ready_agents).
            mode: Scoring mode:
                  - "algorithmic": always use v1 pure-Python scoring (zero API cost).
                  - "llm":         always attempt v2 LLM scoring; falls back to v1 on
                                   any failure.
                  - "auto":        use v2 only when queue has >= 5 items (worth the
                                   ~$0.003 haiku cost); otherwise use v1. This is the
                                   default.

        Returns:
            Reordered list with advisor_score and advisor_reason fields added.
            Returns a copy — does not mutate input items.
        """
        if not queue_items:
            return []

        use_llm = (
            mode == "llm"
            or (mode == "auto" and len(queue_items) >= 5)
        )

        if use_llm:
            result = self.advise_with_llm(queue_items)
            if result:
                return result

        return self._advise_algorithmic(queue_items)

    def format_advice(self, reordered: List[Dict[str, Any]]) -> str:
        """Human-readable advice about the reordered queue.

        Example:
            Launching 'Implement auth' next (score: 87 — unblocks dependents; waited 12m).
            Queue order: [Implement auth (87), Write tests (62), Update docs (41)]

        Args:
            reordered: List returned by advise().

        Returns:
            Multi-line string with next-to-launch info and full queue order.
        """
        if not reordered:
            return "Queue is empty — nothing to advise."

        lines: List[str] = []
        first = reordered[0]
        first_desc = first.get("description", first.get("prompt", "?"))[:60]
        first_score = first.get("advisor_score", 0)
        first_reason = first.get("advisor_reason", "standard priority")

        lines.append(
            f"Launching '{first_desc}' next "
            f"(score: {first_score:.0f} — {first_reason})."
        )

        if len(reordered) > 1:
            queue_parts = []
            for item in reordered:
                desc = item.get("description", item.get("prompt", "?"))[:30]
                score = item.get("advisor_score", 0)
                queue_parts.append(f"{desc} ({score:.0f})")
            lines.append(f"Queue order: [{', '.join(queue_parts)}]")

        return "\n".join(lines)
