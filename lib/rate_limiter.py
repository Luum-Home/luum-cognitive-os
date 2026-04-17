"""Rate Limiter — Prevents token flooding and excessive tool usage.

Tracks tool calls, agent launches, bash commands, and file writes with
configurable per-minute/per-hour limits. Includes cost-per-hour caps.
State is persisted to disk for cross-invocation tracking within a session.

Phase-aware: reads the project phase from cognitive-os.yaml and applies
a multiplier to all limits (reconstruction=1.5x, stabilization=1.0x,
production=0.75x, maintenance=0.5x).

Includes RateLimitQueue for automatic retry of blocked actions after
cooldown expires, with priority ordering and batch reduction suggestions.

Usage:
    from lib.rate_limiter import RateLimiter, RateLimitConfig, RateLimitQueue

    rl = RateLimiter()
    allowed, reason = rl.check("tool_call")
    rl.record("tool_call")
    print(rl.format_status())
    print(rl.format_limit_status())

    # Queue blocked actions for automatic retry
    queue = RateLimitQueue()
    queue_id = queue.enqueue("agent_launch", {"description": "task X"})
    ready = queue.dequeue_ready()

Python 3.9+ compatible. Author: luum.
"""

import json
import math
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from lib.paths import project_root

# Phase modifiers per rules/rate-limiting.md
PHASE_MODIFIERS: Dict[str, float] = {
    "reconstruction": 1.5,
    "stabilization": 1.0,
    "production": 0.75,
    "maintenance": 0.5,
}

# Priority levels for queue ordering (lower number = higher priority)
PRIORITY_HIGH = 1
PRIORITY_NORMAL = 5
PRIORITY_LOW = 10

# Queue constraints
MAX_QUEUE_SIZE = 50
MAX_QUEUE_AGE_SECONDS = 7200  # 2 hours


def _read_phase_from_config(config_path: Optional[str] = None) -> str:
    """Read project phase from cognitive-os.yaml.

    Searches for the file at the given path or common locations.
    Returns the phase string (e.g. 'reconstruction') or 'stabilization'
    as the default (1.0x modifier, safest neutral default).
    """
    paths_to_try: List[str] = []
    if config_path:
        paths_to_try.append(config_path)

    # Common locations via environment variables
    project_dir = project_root()
    if project_dir:
        paths_to_try.append(os.path.join(project_dir, "cognitive-os.yaml"))
        paths_to_try.append(
            os.path.join(project_dir, ".cognitive-os", "cognitive-os.yaml")
        )

    # CWD-relative fallbacks
    paths_to_try.append("cognitive-os.yaml")
    paths_to_try.append(os.path.join(".cognitive-os", "cognitive-os.yaml"))

    for path in paths_to_try:
        if os.path.isfile(path):
            try:
                with open(path, "r") as f:
                    for line in f:
                        match = re.match(r"^\s*phase:\s*(\S+)", line)
                        if match:
                            return match.group(1).strip()
            except OSError:
                continue

    return "stabilization"


def get_phase_modifier(
    phase: Optional[str] = None, config_path: Optional[str] = None
) -> float:
    """Return the rate-limit multiplier for the given or detected phase.

    If *phase* is None, reads it from cognitive-os.yaml.
    Unknown phases default to 1.0 (stabilization-equivalent).
    """
    if phase is None:
        phase = _read_phase_from_config(config_path)
    return PHASE_MODIFIERS.get(phase, 1.0)


@dataclass
class RateLimitConfig:
    """Configuration for rate limit thresholds.

    These are the BASE limits before the phase modifier is applied.
    """

    max_tool_calls_per_minute: int = 30
    max_agent_launches_per_hour: int = 20
    max_bash_commands_per_minute: int = 15
    max_file_writes_per_minute: int = 10
    max_cost_per_hour_usd: float = 5.0
    cooldown_seconds: int = 60


# Window durations in seconds per action type
_WINDOWS: Dict[str, int] = {
    "tool_call": 60,
    "agent_launch": 3600,
    "bash_command": 60,
    "file_write": 60,
}

# Mapping from action type to config field
_LIMITS: Dict[str, str] = {
    "tool_call": "max_tool_calls_per_minute",
    "agent_launch": "max_agent_launches_per_hour",
    "bash_command": "max_bash_commands_per_minute",
    "file_write": "max_file_writes_per_minute",
}

# Valid action types
VALID_ACTIONS = frozenset(_WINDOWS.keys())


@dataclass
class RateLimitState:
    """Mutable state tracking timestamps and cost."""

    tool_calls: List[float] = field(default_factory=list)
    agent_launches: List[float] = field(default_factory=list)
    bash_commands: List[float] = field(default_factory=list)
    file_writes: List[float] = field(default_factory=list)
    cost_usd: float = 0.0
    cost_reset_at: Optional[float] = None  # epoch when hourly cost resets

    def _list_for(self, action_type: str) -> List[float]:
        """Return the timestamp list for the given action type."""
        mapping = {
            "tool_call": self.tool_calls,
            "agent_launch": self.agent_launches,
            "bash_command": self.bash_commands,
            "file_write": self.file_writes,
        }
        return mapping[action_type]

    def to_dict(self) -> Dict:
        return {
            "tool_calls": self.tool_calls,
            "agent_launches": self.agent_launches,
            "bash_commands": self.bash_commands,
            "file_writes": self.file_writes,
            "cost_usd": self.cost_usd,
            "cost_reset_at": self.cost_reset_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "RateLimitState":
        return cls(
            tool_calls=data.get("tool_calls", []),
            agent_launches=data.get("agent_launches", []),
            bash_commands=data.get("bash_commands", []),
            file_writes=data.get("file_writes", []),
            cost_usd=data.get("cost_usd", 0.0),
            cost_reset_at=data.get("cost_reset_at"),
        )


class RateLimiter:
    """Rate limiter with file-persisted state, configurable thresholds,
    and phase-aware limit scaling."""

    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        state_path: str = ".cognitive-os/rate-limit-state.json",
        phase: Optional[str] = None,
        config_path: Optional[str] = None,
    ):
        self.config = config or RateLimitConfig()
        self.state_path = state_path
        self.state = self._load_state()

        # Resolve phase and modifier
        if phase is not None:
            self._phase = phase
        else:
            self._phase = _read_phase_from_config(config_path)
        self._phase_modifier = PHASE_MODIFIERS.get(self._phase, 1.0)

    @property
    def phase(self) -> str:
        """Current project phase."""
        return self._phase

    @property
    def phase_modifier(self) -> float:
        """Multiplier applied to all base limits for the current phase."""
        return self._phase_modifier

    def effective_limit(self, action_type: str) -> int:
        """Return the effective (phase-adjusted) limit for an action type."""
        base = getattr(self.config, _LIMITS[action_type])
        return max(1, math.floor(base * self._phase_modifier))

    def check(self, action_type: str) -> Tuple[bool, str]:
        """Check if an action is allowed under current rate limits.

        Limits are scaled by the phase modifier before comparison.

        Args:
            action_type: One of "tool_call", "agent_launch", "bash_command",
                         "file_write".

        Returns:
            (allowed, reason) -- allowed is True if the action can proceed,
            reason explains why it was blocked.
        """
        if action_type not in VALID_ACTIONS:
            return True, "unknown action type, allowing"

        self._cleanup_old_entries()

        # Check cost cap (hourly) -- cost cap is also phase-adjusted
        effective_cost_cap = self.config.max_cost_per_hour_usd * self._phase_modifier
        if self.state.cost_usd >= effective_cost_cap:
            return False, (
                f"Hourly cost cap exceeded: ${self.state.cost_usd:.2f} "
                f">= ${effective_cost_cap:.2f} "
                f"(base ${self.config.max_cost_per_hour_usd:.2f} "
                f"x {self._phase_modifier} [{self._phase}])"
            )

        # Check count limit for this action type (phase-adjusted)
        timestamps = self.state._list_for(action_type)
        limit = self.effective_limit(action_type)
        window = _WINDOWS[action_type]

        now = time.time()
        recent = [t for t in timestamps if now - t < window]

        if len(recent) >= limit:
            base_limit = getattr(self.config, _LIMITS[action_type])
            window_label = "minute" if window == 60 else "hour"
            return False, (
                f"{action_type} limit exceeded: {len(recent)}/{limit} "
                f"per {window_label} "
                f"(base {base_limit} x {self._phase_modifier} [{self._phase}]). "
                f"Wait {self.config.cooldown_seconds}s."
            )

        return True, "within limits"

    def record(self, action_type: str, cost_usd: float = 0.0) -> None:
        """Record an action for rate tracking.

        Args:
            action_type: One of the valid action types.
            cost_usd: Cost in USD for this action (default 0.0).
        """
        if action_type not in VALID_ACTIONS:
            return

        now = time.time()
        self.state._list_for(action_type).append(now)

        # Track cost with hourly reset
        if self.state.cost_reset_at is None or now >= self.state.cost_reset_at:
            self.state.cost_usd = 0.0
            self.state.cost_reset_at = now + 3600

        self.state.cost_usd += cost_usd
        self._save_state()

    def get_status(self) -> Dict:
        """Current rate limit status with remaining quota per type.

        All limits reflect phase-adjusted effective values.
        """
        self._cleanup_old_entries()
        now = time.time()
        status: Dict = {}

        for action_type in VALID_ACTIONS:
            timestamps = self.state._list_for(action_type)
            limit = self.effective_limit(action_type)
            base_limit = getattr(self.config, _LIMITS[action_type])
            window = _WINDOWS[action_type]
            recent = [t for t in timestamps if now - t < window]
            status[action_type] = {
                "used": len(recent),
                "limit": limit,
                "base_limit": base_limit,
                "remaining": max(0, limit - len(recent)),
                "window_seconds": window,
            }

        effective_cost_cap = self.config.max_cost_per_hour_usd * self._phase_modifier
        status["cost"] = {
            "used_usd": round(self.state.cost_usd, 4),
            "limit_usd": round(effective_cost_cap, 4),
            "base_limit_usd": self.config.max_cost_per_hour_usd,
            "remaining_usd": round(
                max(0.0, effective_cost_cap - self.state.cost_usd), 4
            ),
        }

        status["phase"] = self._phase
        status["phase_modifier"] = self._phase_modifier

        return status

    def reset(self) -> None:
        """Reset all counters (manual override)."""
        self.state = RateLimitState()
        self._save_state()

    def format_status(self) -> str:
        """Human-readable status with phase, effective limits, and quotas."""
        status = self.get_status()
        lines = [
            f"Rate Limit Status (phase: {self._phase}, "
            f"modifier: {self._phase_modifier}x):"
        ]
        for action_type in sorted(VALID_ACTIONS):
            s = status[action_type]
            window_label = "min" if s["window_seconds"] == 60 else "hr"
            lines.append(
                f"  {action_type}: {s['used']}/{s['limit']} per {window_label} "
                f"(base {s['base_limit']}, {s['remaining']} remaining)"
            )
        cost = status["cost"]
        lines.append(
            f"  cost: ${cost['used_usd']:.2f}/${cost['limit_usd']:.2f} per hr "
            f"(base ${cost['base_limit_usd']:.2f}, "
            f"${cost['remaining_usd']:.2f} remaining)"
        )
        return "\n".join(lines)

    def format_limit_status(self, queue: Optional["RateLimitQueue"] = None) -> str:
        """Detailed human-readable status with percentages and queue info.

        Provides a dashboard-style view suitable for the orchestrator to
        display when rate limits are approaching or exceeded.

        Args:
            queue: Optional RateLimitQueue to include queue status.
        """
        status = self.get_status()
        lines = [
            f"Rate Limits (phase: {self._phase}, "
            f"modifier: {self._phase_modifier}x):"
        ]

        # Display each action type with percentage
        display_order = ["agent_launch", "bash_command", "file_write", "tool_call"]
        display_names = {
            "agent_launch": "Agent launches",
            "bash_command": "Bash commands",
            "file_write": "File writes",
            "tool_call": "Tool calls",
        }
        for action_type in display_order:
            if action_type not in status:
                continue
            s = status[action_type]
            window_label = "minute" if s["window_seconds"] == 60 else "hour"
            pct = (s["used"] / s["limit"] * 100) if s["limit"] > 0 else 0
            name = display_names.get(action_type, action_type)
            lines.append(
                f"  {name}: {s['used']}/{s['limit']} per {window_label} "
                f"({pct:.0f}%) -- {s['remaining']} remaining"
            )

        # Cost line
        cost = status["cost"]
        cost_pct = (
            (cost["used_usd"] / cost["limit_usd"] * 100)
            if cost["limit_usd"] > 0
            else 0
        )
        lines.append(
            f"  Cost: ${cost['used_usd']:.2f}/${cost['limit_usd']:.2f} per hour "
            f"({cost_pct:.0f}%)"
        )

        # Queue info if provided
        if queue is not None:
            items = queue.peek()
            if items:
                now = time.time()
                # Find next eligible item
                next_eligible_in = None
                for item in items:
                    eligible_at = item.get("eligible_at", 0)
                    if eligible_at > now:
                        next_eligible_in = int(eligible_at - now)
                        break
                queue_line = f"\n  Queue: {len(items)} items waiting"
                if next_eligible_in is not None:
                    queue_line += f" (next eligible in {next_eligible_in}s)"
                lines.append(queue_line)
            else:
                lines.append("\n  Queue: empty")

        return "\n".join(lines)

    def suggest_reduction(self, queued_count: int) -> str:
        """Suggest batch reductions when rate limits are hit.

        Analyzes the current queue size and rate limit status to provide
        actionable suggestions for reducing pressure.

        Args:
            queued_count: Number of items currently in the queue.

        Returns:
            Human-readable suggestion string, or empty string if no
            suggestion is warranted.
        """
        if queued_count <= 2:
            return ""

        suggestions: List[str] = []
        status = self.get_status()

        # Suggest batching when many agents are queued
        if queued_count > 3:
            batched = max(1, queued_count // 2)
            suggestions.append(
                f"You have {queued_count} agents queued. "
                f"Consider batching into {batched} larger agents."
            )

        # Show current rate vs limit for agent launches
        agent_status = status.get("agent_launch", {})
        if agent_status:
            suggestions.append(
                f"Current rate: {agent_status['used']}/{agent_status['limit']}/hr "
                f"(phase: {self._phase}). "
                f"Next slot available in ~{self.config.cooldown_seconds}s."
            )

        # Suggest model downgrade if cost is the bottleneck
        cost = status.get("cost", {})
        if cost.get("remaining_usd", 999) < 1.0 and queued_count > 2:
            suggestions.append(
                f"Consider using model: haiku for {queued_count - 1} of "
                f"these tasks to reduce cost pressure."
            )

        return "\n".join(suggestions)

    def _cleanup_old_entries(self) -> None:
        """Remove entries older than their respective window."""
        now = time.time()
        for action_type in VALID_ACTIONS:
            window = _WINDOWS[action_type]
            timestamps = self.state._list_for(action_type)
            # Filter in place
            fresh = [t for t in timestamps if now - t < window]
            # Replace the list contents
            if action_type == "tool_call":
                self.state.tool_calls = fresh
            elif action_type == "agent_launch":
                self.state.agent_launches = fresh
            elif action_type == "bash_command":
                self.state.bash_commands = fresh
            elif action_type == "file_write":
                self.state.file_writes = fresh

        # Reset cost if hour elapsed
        if (
            self.state.cost_reset_at is not None
            and now >= self.state.cost_reset_at
        ):
            self.state.cost_usd = 0.0
            self.state.cost_reset_at = None

    def _load_state(self) -> RateLimitState:
        """Load state from file or create fresh."""
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                return RateLimitState.from_dict(data)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        return RateLimitState()

    def _save_state(self) -> None:
        """Persist state to file."""
        try:
            os.makedirs(os.path.dirname(self.state_path) or ".", exist_ok=True)
            with open(self.state_path, "w") as f:
                json.dump(self.state.to_dict(), f)
        except OSError:
            pass  # Best effort -- don't crash on I/O failure


class RateLimitQueue:
    """Queues blocked actions for automatic retry after cooldown.

    When the rate limiter blocks an action (exit 2), instead of dropping
    it the orchestrator can enqueue it here. The queue persists to disk
    and items become eligible for dequeue once their cooldown expires.

    Items are dequeued in priority order (lower number = higher priority),
    then FIFO within the same priority level.

    Constraints:
    - Max 50 items in queue (oldest auto-pruned on overflow)
    - Items older than 2 hours are auto-pruned
    - State persisted to .cognitive-os/rate-limit-queue.json
    """

    def __init__(
        self,
        state_path: str = ".cognitive-os/rate-limit-queue.json",
        cooldown_seconds: int = 60,
    ):
        self.state_path = state_path
        self.cooldown_seconds = cooldown_seconds
        self._items: List[Dict[str, Any]] = self._load()

    def enqueue(
        self,
        action_type: str,
        context: Optional[Dict[str, Any]] = None,
        priority: int = PRIORITY_NORMAL,
    ) -> str:
        """Queue a blocked action for retry after cooldown.

        Args:
            action_type: The action type that was blocked (e.g. "agent_launch").
            context: Optional dict with description, estimated_tokens, model,
                     or any metadata the orchestrator needs to re-launch.
            priority: Priority level (1=high, 5=normal, 10=low). Lower
                      numbers dequeue first.

        Returns:
            A unique queue_id string for tracking or cancellation.
        """
        self._prune()

        now = time.time()
        queue_id = str(uuid.uuid4())[:8]
        item: Dict[str, Any] = {
            "queue_id": queue_id,
            "action_type": action_type,
            "context": context or {},
            "priority": priority,
            "enqueued_at": now,
            "eligible_at": now + self.cooldown_seconds,
        }

        self._items.append(item)

        # Enforce max size -- drop oldest low-priority items first
        if len(self._items) > MAX_QUEUE_SIZE:
            # Sort by priority desc then enqueued_at asc (oldest low-pri first)
            self._items.sort(key=lambda x: (-x["priority"], x["enqueued_at"]))
            self._items = self._items[:MAX_QUEUE_SIZE]

        self._save()
        return queue_id

    def dequeue_ready(self) -> List[Dict[str, Any]]:
        """Return and remove items whose cooldown has expired.

        Items are returned sorted by priority (lowest first), then
        by enqueue time (FIFO within same priority).

        Returns:
            List of queue items that are now eligible for execution.
        """
        self._prune()
        now = time.time()

        ready: List[Dict[str, Any]] = []
        remaining: List[Dict[str, Any]] = []

        for item in self._items:
            if item["eligible_at"] <= now:
                ready.append(item)
            else:
                remaining.append(item)

        # Sort ready items: priority asc, then enqueued_at asc (FIFO)
        ready.sort(key=lambda x: (x["priority"], x["enqueued_at"]))

        self._items = remaining
        self._save()
        return ready

    def peek(self) -> List[Dict[str, Any]]:
        """Show queued items without removing them.

        Returns items sorted by priority then enqueue time.
        """
        self._prune()
        items = list(self._items)
        items.sort(key=lambda x: (x["priority"], x["enqueued_at"]))
        return items

    def cancel(self, queue_id: str) -> bool:
        """Cancel a queued action by its queue_id.

        Args:
            queue_id: The ID returned by enqueue().

        Returns:
            True if the item was found and removed, False otherwise.
        """
        before = len(self._items)
        self._items = [i for i in self._items if i["queue_id"] != queue_id]
        removed = len(self._items) < before
        if removed:
            self._save()
        return removed

    def format_queue_status(self) -> str:
        """Human-readable queue status for the orchestrator.

        Returns:
            Multi-line string describing queue contents and timing.
        """
        items = self.peek()
        if not items:
            return "Rate Limit Queue: empty"

        now = time.time()
        lines = [f"Rate Limit Queue: {len(items)} item(s)"]
        for i, item in enumerate(items, 1):
            desc = item.get("context", {}).get("description", "no description")
            # Truncate long descriptions
            if len(desc) > 60:
                desc = desc[:57] + "..."
            wait = max(0, int(item["eligible_at"] - now))
            pri_label = {
                PRIORITY_HIGH: "HIGH",
                PRIORITY_NORMAL: "NORMAL",
                PRIORITY_LOW: "LOW",
            }.get(item["priority"], f"P{item['priority']}")
            if wait > 0:
                lines.append(
                    f"  {i}. [{pri_label}] {item['action_type']}: "
                    f"{desc} (eligible in {wait}s)"
                )
            else:
                lines.append(
                    f"  {i}. [{pri_label}] {item['action_type']}: "
                    f"{desc} (READY)"
                )
        return "\n".join(lines)

    def _prune(self) -> None:
        """Remove items older than MAX_QUEUE_AGE_SECONDS."""
        now = time.time()
        cutoff = now - MAX_QUEUE_AGE_SECONDS
        before = len(self._items)
        self._items = [i for i in self._items if i["enqueued_at"] > cutoff]
        if len(self._items) < before:
            self._save()

    def _load(self) -> List[Dict[str, Any]]:
        """Load queue from disk."""
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
            except (json.JSONDecodeError, TypeError, OSError):
                pass
        return []

    def _save(self) -> None:
        """Persist queue to disk."""
        try:
            os.makedirs(os.path.dirname(self.state_path) or ".", exist_ok=True)
            with open(self.state_path, "w") as f:
                json.dump(self._items, f)
        except OSError:
            pass  # Best effort
