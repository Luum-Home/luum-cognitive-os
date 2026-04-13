# scope: both
"""Rate Limit Protection — Detect approaching API rate limits and auto-pause.

Monitors token consumption per session and warns/pauses before hitting
API rate limits. Thresholds: 50% INFO, 80% WARN, 95% BLOCK.

Author: luum
Python 3.9+ compatible.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class RateLimitStatus:
    """Current rate limit status snapshot."""

    tokens_used_session: int
    tokens_estimated_remaining: int
    pct_used: float  # 0.0-1.0
    agents_launched: int
    time_in_session_minutes: float
    estimated_reset_time: Optional[str]
    should_pause: bool
    reason: str


# Default token estimates per action type.
_DEFAULT_ACTION_ESTIMATES: Dict[str, int] = {
    "agent_launch": 150_000,
    "bash_command": 2_000,
    "file_read": 1_000,
    "file_write": 500,
}


class RateLimitProtection:
    """Monitors token consumption and warns/pauses before hitting API limits.

    Thresholds (configurable via cognitive-os.yaml):
    - 50%: INFO  -- "Halfway through estimated budget"
    - 80%: WARN  -- "Approaching limit. Consider pausing agent launches."
    - 95%: BLOCK -- "Auto-pausing agent launches. Resume after reset."
    """

    def __init__(
        self,
        cost_events_path: str = ".cognitive-os/metrics/cost-events.jsonl",
        config_path: str = "cognitive-os.yaml",
    ) -> None:
        self.cost_events_path = cost_events_path
        self.config_path = config_path

        # Defaults -- overridden by _load_config if available.
        self.hourly_token_limit: int = 5_000_000
        self.daily_token_limit: int = 50_000_000
        self.max_agents_per_hour: int = 30

        self.threshold_info: float = 0.50
        self.threshold_warn: float = 0.80
        self.threshold_block: float = 0.95

        self._session_start = time.time()
        self._session_tokens_in: int = 0
        self._session_tokens_out: int = 0
        self._session_agents: int = 0

        self._load_config()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        """Load limits from cognitive-os.yaml if present."""
        try:
            import yaml  # type: ignore[import-untyped]

            path = Path(self.config_path)
            if not path.exists():
                return
            with open(path) as fh:
                cfg = yaml.safe_load(fh) or {}
            rl = (cfg.get("resources") or {}).get("rate_limit") or {}
            if "hourly_token_limit" in rl:
                self.hourly_token_limit = int(rl["hourly_token_limit"])
            if "daily_token_limit" in rl:
                self.daily_token_limit = int(rl["daily_token_limit"])
            if "max_agents_per_hour" in rl:
                self.max_agents_per_hour = int(rl["max_agents_per_hour"])
            thresholds = rl.get("thresholds") or {}
            if "info" in thresholds:
                self.threshold_info = float(thresholds["info"])
            if "warn" in thresholds:
                self.threshold_warn = float(thresholds["warn"])
            if "block" in thresholds:
                self.threshold_block = float(thresholds["block"])
        except Exception:
            pass  # Graceful degradation -- use defaults.

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def check(self) -> RateLimitStatus:
        """Check current rate limit status.

        Reads from cost-events.jsonl to count tokens used in the current
        hour window. Estimates remaining based on hourly/daily limits.
        """
        hourly = self._hourly_usage()
        tokens_used = hourly["tokens"]
        agents = hourly["agents"]

        pct = tokens_used / self.hourly_token_limit if self.hourly_token_limit > 0 else 0.0
        pct = min(pct, 1.0)
        remaining = max(self.hourly_token_limit - tokens_used, 0)

        elapsed = (time.time() - self._session_start) / 60.0
        reset_minutes = max(60.0 - (elapsed % 60.0), 0)
        reset_time = (
            datetime.now(timezone.utc) + timedelta(minutes=reset_minutes)
        ).isoformat()

        should_pause = pct >= self.threshold_block
        if should_pause:
            reason = f"Token usage at {pct:.0%} of hourly limit ({tokens_used:,}/{self.hourly_token_limit:,})"
        elif pct >= self.threshold_warn:
            reason = f"Approaching limit: {pct:.0%} used"
        elif pct >= self.threshold_info:
            reason = f"Halfway through budget: {pct:.0%} used"
        else:
            reason = "Within safe limits"

        return RateLimitStatus(
            tokens_used_session=tokens_used,
            tokens_estimated_remaining=remaining,
            pct_used=pct,
            agents_launched=agents,
            time_in_session_minutes=elapsed,
            estimated_reset_time=reset_time,
            should_pause=should_pause,
            reason=reason,
        )

    def should_launch_agent(self) -> Tuple[bool, str]:
        """Pre-check before launching any agent.

        Returns ``(allowed, reason)``.
        Blocked if: >95% tokens used, >30 agents this hour, or daily
        limit exceeded.
        """
        if os.environ.get("RATE_LIMIT_OVERRIDE", "").lower() == "true":
            return True, "Override active (RATE_LIMIT_OVERRIDE=true)"

        status = self.check()
        if status.should_pause:
            return False, f"BLOCKED: {status.reason}. Resume after reset (~{self._minutes_to_reset():.0f} min)."

        hourly = self._hourly_usage()
        if hourly["agents"] >= self.max_agents_per_hour:
            return False, f"BLOCKED: Agent limit reached ({hourly['agents']}/{self.max_agents_per_hour} this hour)."

        daily = self._daily_usage()
        if daily["tokens"] >= self.daily_token_limit:
            return False, f"BLOCKED: Daily token limit reached ({daily['tokens']:,}/{self.daily_token_limit:,})."

        return True, "OK"

    def record_usage(
        self, tokens_in: int, tokens_out: int, model: str, action: str
    ) -> None:
        """Record token usage for tracking.

        Appends to cost-events.jsonl and updates in-memory counters.
        """
        self._session_tokens_in += tokens_in
        self._session_tokens_out += tokens_out
        if action == "agent_launch":
            self._session_agents += 1

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "action": action,
            "input_tokens": tokens_in,
            "output_tokens": tokens_out,
            "total_tokens": tokens_in + tokens_out,
        }

        path = Path(self.cost_events_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as fh:
            fh.write(json.dumps(entry) + "\n")

    def estimate_action_cost_tokens(self, action_type: str) -> int:
        """Estimate tokens for common actions.

        ``agent_launch``: ~150K tokens average
        ``bash_command``: ~2K tokens
        ``file_read``:    ~1K tokens
        ``file_write``:   ~500 tokens
        """
        return _DEFAULT_ACTION_ESTIMATES.get(action_type, 2_000)

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def format_status(self) -> str:
        """One-line status for display."""
        status = self.check()
        reset_min = self._minutes_to_reset()
        return (
            f"Tokens: {self._human(status.tokens_used_session)}"
            f"/{self._human(self.hourly_token_limit)}"
            f" ({status.pct_used:.0%})"
            f" | Agents: {status.agents_launched}/{self.max_agents_per_hour}"
            f" | Reset: {reset_min:.0f}min"
        )

    def format_warning(self) -> str:
        """Warning message when approaching limits."""
        status = self.check()
        reset_min = self._minutes_to_reset()
        return (
            f"WARNING: {status.pct_used:.0%} of hourly token limit used "
            f"({self._human(status.tokens_used_session)}/{self._human(self.hourly_token_limit)}).\n"
            f"{status.agents_launched} agents launched this hour.\n"
            f"Consider pausing agent launches.\n"
            f"Estimated reset: {reset_min:.0f} minutes."
        )

    def format_block(self) -> str:
        """Block message when at limit."""
        status = self.check()
        reset_min = self._minutes_to_reset()
        return (
            f"RATE LIMIT REACHED ({status.pct_used:.0%}). Auto-pausing agent launches.\n"
            f"Session state saved. Resume after reset (~{reset_min:.0f} min).\n"
            f"To force continue: set RATE_LIMIT_OVERRIDE=true"
        )

    # ------------------------------------------------------------------
    # Session resume support
    # ------------------------------------------------------------------

    def save_session_for_resume(self) -> None:
        """Save current session state so work can resume after reset.

        Writes to ``.cognitive-os/rate-limit-pause.json``.
        """
        status = self.check()
        state = {
            "paused_at": datetime.now(timezone.utc).isoformat(),
            "tokens_used": status.tokens_used_session,
            "agents_launched": status.agents_launched,
            "pct_used": round(status.pct_used, 4),
            "estimated_reset_time": status.estimated_reset_time,
            "reason": status.reason,
            "session_minutes": round(status.time_in_session_minutes, 1),
        }
        path = Path(".cognitive-os/rate-limit-pause.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as fh:
            json.dump(state, fh, indent=2)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _hourly_usage(self) -> Dict[str, int]:
        """Sum tokens and count agents from cost-events in the last hour."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        return self._aggregate_since(cutoff)

    def _daily_usage(self) -> Dict[str, int]:
        """Sum tokens and count agents from cost-events in the last 24h."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        return self._aggregate_since(cutoff)

    def _aggregate_since(self, cutoff: datetime) -> Dict[str, int]:
        """Read cost-events.jsonl and aggregate entries since *cutoff*."""
        tokens = self._session_tokens_in + self._session_tokens_out
        agents = self._session_agents

        path = Path(self.cost_events_path)
        if not path.exists():
            return {"tokens": tokens, "agents": agents}

        try:
            with open(path) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts_str = entry.get("timestamp", "")
                    try:
                        ts = datetime.fromisoformat(ts_str)
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        continue
                    if ts < cutoff:
                        continue
                    tokens += entry.get("total_tokens", 0) or (
                        entry.get("input_tokens", 0) + entry.get("output_tokens", 0)
                    )
                    if entry.get("action") == "agent_launch":
                        agents += 1
        except OSError:
            pass

        return {"tokens": tokens, "agents": agents}

    def _minutes_to_reset(self) -> float:
        elapsed = (time.time() - self._session_start) / 60.0
        return max(60.0 - (elapsed % 60.0), 0)

    @staticmethod
    def _human(n: int) -> str:
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.0f}K"
        return str(n)
