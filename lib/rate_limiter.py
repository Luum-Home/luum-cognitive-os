"""Rate Limiter — Prevents token flooding and excessive tool usage.

Tracks tool calls, agent launches, bash commands, and file writes with
configurable per-minute/per-hour limits. Includes cost-per-hour caps.
State is persisted to disk for cross-invocation tracking within a session.

Usage:
    from lib.rate_limiter import RateLimiter, RateLimitConfig

    rl = RateLimiter()
    allowed, reason = rl.check("tool_call")
    rl.record("tool_call")
    print(rl.format_status())

Python 3.9+ compatible. Author: luum.
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


@dataclass
class RateLimitConfig:
    """Configuration for rate limit thresholds."""

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
    """Rate limiter with file-persisted state and configurable thresholds."""

    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        state_path: str = ".cognitive-os/rate-limit-state.json",
    ):
        self.config = config or RateLimitConfig()
        self.state_path = state_path
        self.state = self._load_state()

    def check(self, action_type: str) -> Tuple[bool, str]:
        """Check if an action is allowed under current rate limits.

        Args:
            action_type: One of "tool_call", "agent_launch", "bash_command",
                         "file_write".

        Returns:
            (allowed, reason) — allowed is True if the action can proceed,
            reason explains why it was blocked.
        """
        if action_type not in VALID_ACTIONS:
            return True, "unknown action type, allowing"

        self._cleanup_old_entries()

        # Check cost cap (hourly)
        if self.state.cost_usd >= self.config.max_cost_per_hour_usd:
            return False, (
                f"Hourly cost cap exceeded: ${self.state.cost_usd:.2f} "
                f">= ${self.config.max_cost_per_hour_usd:.2f}"
            )

        # Check count limit for this action type
        timestamps = self.state._list_for(action_type)
        limit = getattr(self.config, _LIMITS[action_type])
        window = _WINDOWS[action_type]

        now = time.time()
        recent = [t for t in timestamps if now - t < window]

        if len(recent) >= limit:
            window_label = "minute" if window == 60 else "hour"
            return False, (
                f"{action_type} limit exceeded: {len(recent)}/{limit} "
                f"per {window_label}. Wait {self.config.cooldown_seconds}s."
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
        """Current rate limit status with remaining quota per type."""
        self._cleanup_old_entries()
        now = time.time()
        status: Dict = {}

        for action_type in VALID_ACTIONS:
            timestamps = self.state._list_for(action_type)
            limit = getattr(self.config, _LIMITS[action_type])
            window = _WINDOWS[action_type]
            recent = [t for t in timestamps if now - t < window]
            status[action_type] = {
                "used": len(recent),
                "limit": limit,
                "remaining": max(0, limit - len(recent)),
                "window_seconds": window,
            }

        status["cost"] = {
            "used_usd": round(self.state.cost_usd, 4),
            "limit_usd": self.config.max_cost_per_hour_usd,
            "remaining_usd": round(
                max(0.0, self.config.max_cost_per_hour_usd - self.state.cost_usd), 4
            ),
        }

        return status

    def reset(self) -> None:
        """Reset all counters (manual override)."""
        self.state = RateLimitState()
        self._save_state()

    def format_status(self) -> str:
        """Human-readable status with remaining quotas and cooldowns."""
        status = self.get_status()
        lines = ["Rate Limit Status:"]
        for action_type in sorted(VALID_ACTIONS):
            s = status[action_type]
            window_label = "min" if s["window_seconds"] == 60 else "hr"
            lines.append(
                f"  {action_type}: {s['used']}/{s['limit']} per {window_label} "
                f"({s['remaining']} remaining)"
            )
        cost = status["cost"]
        lines.append(
            f"  cost: ${cost['used_usd']:.2f}/${cost['limit_usd']:.2f} per hr "
            f"(${cost['remaining_usd']:.2f} remaining)"
        )
        return "\n".join(lines)

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
            pass  # Best effort — don't crash on I/O failure
