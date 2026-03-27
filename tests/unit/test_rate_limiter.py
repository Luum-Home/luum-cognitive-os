"""Unit tests for lib/rate_limiter.py

Validates rate limiting logic: check/record/status/reset/cleanup,
cost tracking, state persistence, custom configs, and edge cases.
"""

import json
import time

import pytest

from lib.rate_limiter import (
    VALID_ACTIONS,
    RateLimitConfig,
    RateLimiter,
    RateLimitState,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_limiter(tmp_path, **config_overrides):
    """Create a RateLimiter with a temp state file and optional config."""
    cfg = RateLimitConfig(**config_overrides)
    return RateLimiter(config=cfg, state_path=str(tmp_path / "state.json"))


# ---------------------------------------------------------------------------
# check — within limits
# ---------------------------------------------------------------------------


class TestCheckWithinLimits:
    """Actions within limits should be allowed."""

    def test_first_call_always_allowed(self, tmp_path):
        """The very first call of any type must always succeed."""
        rl = _make_limiter(tmp_path)
        allowed, reason = rl.check("tool_call")
        assert allowed is True
        assert "within limits" in reason.lower() or "unknown" in reason.lower()

    def test_all_action_types_allowed_initially(self, tmp_path):
        """Every valid action type should be allowed on first check."""
        rl = _make_limiter(tmp_path)
        for action in VALID_ACTIONS:
            allowed, _ = rl.check(action)
            assert allowed is True, f"{action} should be allowed initially"

    def test_unknown_action_type_allowed(self, tmp_path):
        """Unknown action types should pass through (not crash)."""
        rl = _make_limiter(tmp_path)
        allowed, reason = rl.check("unknown_type")
        assert allowed is True


# ---------------------------------------------------------------------------
# check — blocks when exceeded
# ---------------------------------------------------------------------------


class TestCheckBlocks:
    """Actions exceeding limits should be blocked."""

    def test_blocks_tool_calls_at_limit(self, tmp_path):
        """Should block when tool_call count exceeds max_tool_calls_per_minute."""
        rl = _make_limiter(tmp_path, max_tool_calls_per_minute=3)
        for _ in range(3):
            rl.record("tool_call")
        allowed, reason = rl.check("tool_call")
        assert allowed is False
        assert "tool_call" in reason
        assert "limit exceeded" in reason.lower()

    def test_blocks_agent_launches_at_limit(self, tmp_path):
        """Should block when agent_launch count exceeds max_agent_launches_per_hour."""
        rl = _make_limiter(tmp_path, max_agent_launches_per_hour=2)
        for _ in range(2):
            rl.record("agent_launch")
        allowed, reason = rl.check("agent_launch")
        assert allowed is False
        assert "agent_launch" in reason

    def test_blocks_bash_commands_at_limit(self, tmp_path):
        """Should block when bash_command count exceeds limit."""
        rl = _make_limiter(tmp_path, max_bash_commands_per_minute=2)
        for _ in range(2):
            rl.record("bash_command")
        allowed, reason = rl.check("bash_command")
        assert allowed is False
        assert "bash_command" in reason

    def test_blocks_file_writes_at_limit(self, tmp_path):
        """Should block when file_write count exceeds limit."""
        rl = _make_limiter(tmp_path, max_file_writes_per_minute=2)
        for _ in range(2):
            rl.record("file_write")
        allowed, reason = rl.check("file_write")
        assert allowed is False

    def test_blocks_when_cost_exceeded(self, tmp_path):
        """Should block when hourly cost cap is exceeded."""
        rl = _make_limiter(tmp_path, max_cost_per_hour_usd=1.0)
        rl.record("tool_call", cost_usd=1.5)
        allowed, reason = rl.check("tool_call")
        assert allowed is False
        assert "cost cap" in reason.lower()


# ---------------------------------------------------------------------------
# record
# ---------------------------------------------------------------------------


class TestRecord:
    """Recording actions should increment counters."""

    def test_record_increments_counter(self, tmp_path):
        """Each record call should add one timestamp."""
        rl = _make_limiter(tmp_path)
        rl.record("tool_call")
        rl.record("tool_call")
        status = rl.get_status()
        assert status["tool_call"]["used"] == 2

    def test_record_unknown_type_is_noop(self, tmp_path):
        """Recording an unknown type should not crash or affect state."""
        rl = _make_limiter(tmp_path)
        rl.record("nonexistent_type")
        # No exception, state unchanged
        status = rl.get_status()
        for action in VALID_ACTIONS:
            assert status[action]["used"] == 0

    def test_record_accumulates_cost(self, tmp_path):
        """Cost should accumulate across multiple records."""
        rl = _make_limiter(tmp_path)
        rl.record("tool_call", cost_usd=0.50)
        rl.record("agent_launch", cost_usd=0.75)
        status = rl.get_status()
        assert abs(status["cost"]["used_usd"] - 1.25) < 0.01


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------


class TestCleanup:
    """Old entries should be removed after their window expires."""

    def test_cleanup_removes_old_entries(self, tmp_path):
        """Entries older than the window should be cleaned up."""
        rl = _make_limiter(tmp_path, max_tool_calls_per_minute=100)
        # Inject timestamps 120 seconds in the past
        old_time = time.time() - 120
        rl.state.tool_calls = [old_time, old_time + 1]
        rl._cleanup_old_entries()
        assert len(rl.state.tool_calls) == 0

    def test_cleanup_keeps_recent_entries(self, tmp_path):
        """Entries within the window should be preserved."""
        rl = _make_limiter(tmp_path)
        now = time.time()
        rl.state.tool_calls = [now - 10, now - 5, now]
        rl._cleanup_old_entries()
        assert len(rl.state.tool_calls) == 3


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------


class TestGetStatus:
    """Status should show remaining quotas for all types."""

    def test_status_shows_remaining_quota(self, tmp_path):
        """Status should report correct remaining quota."""
        rl = _make_limiter(tmp_path, max_tool_calls_per_minute=10)
        rl.record("tool_call")
        rl.record("tool_call")
        status = rl.get_status()
        assert status["tool_call"]["remaining"] == 8
        assert status["tool_call"]["used"] == 2
        assert status["tool_call"]["limit"] == 10

    def test_status_includes_all_action_types(self, tmp_path):
        """Status dict should contain entries for every valid action type."""
        rl = _make_limiter(tmp_path)
        status = rl.get_status()
        for action in VALID_ACTIONS:
            assert action in status
        assert "cost" in status

    def test_status_cost_remaining(self, tmp_path):
        """Cost remaining should decrease as cost is recorded."""
        rl = _make_limiter(tmp_path, max_cost_per_hour_usd=10.0)
        rl.record("tool_call", cost_usd=3.0)
        status = rl.get_status()
        assert abs(status["cost"]["remaining_usd"] - 7.0) < 0.01


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------


class TestReset:
    """Reset should clear all counters."""

    def test_reset_clears_all_counters(self, tmp_path):
        """After reset, all counters should be zero."""
        rl = _make_limiter(tmp_path)
        rl.record("tool_call")
        rl.record("agent_launch")
        rl.record("bash_command")
        rl.record("file_write", cost_usd=2.0)
        rl.reset()
        status = rl.get_status()
        for action in VALID_ACTIONS:
            assert status[action]["used"] == 0
        assert status["cost"]["used_usd"] == 0.0


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------


class TestStatePersistence:
    """State should survive save/load roundtrip."""

    def test_load_save_roundtrip(self, tmp_path):
        """State saved to disk should be recoverable by a new instance."""
        state_path = str(tmp_path / "state.json")
        rl1 = RateLimiter(
            config=RateLimitConfig(max_tool_calls_per_minute=50),
            state_path=state_path,
        )
        rl1.record("tool_call")
        rl1.record("tool_call")
        rl1.record("agent_launch", cost_usd=0.5)

        # New instance loading from same path
        rl2 = RateLimiter(
            config=RateLimitConfig(max_tool_calls_per_minute=50),
            state_path=state_path,
        )
        status = rl2.get_status()
        assert status["tool_call"]["used"] == 2
        assert status["agent_launch"]["used"] == 1

    def test_load_from_nonexistent_creates_fresh(self, tmp_path):
        """Loading from a non-existent file should create fresh state."""
        rl = RateLimiter(state_path=str(tmp_path / "nope.json"))
        status = rl.get_status()
        for action in VALID_ACTIONS:
            assert status[action]["used"] == 0

    def test_load_from_corrupted_file_creates_fresh(self, tmp_path):
        """Loading from a corrupted JSON file should create fresh state."""
        state_file = tmp_path / "state.json"
        state_file.write_text("not valid json {{{")
        rl = RateLimiter(state_path=str(state_file))
        status = rl.get_status()
        for action in VALID_ACTIONS:
            assert status[action]["used"] == 0


# ---------------------------------------------------------------------------
# Custom config
# ---------------------------------------------------------------------------


class TestCustomConfig:
    """Custom config should override defaults."""

    def test_custom_config_overrides_defaults(self, tmp_path):
        """Custom config values should be used instead of defaults."""
        rl = _make_limiter(
            tmp_path,
            max_tool_calls_per_minute=5,
            max_agent_launches_per_hour=3,
            max_cost_per_hour_usd=1.0,
        )
        assert rl.config.max_tool_calls_per_minute == 5
        assert rl.config.max_agent_launches_per_hour == 3
        assert rl.config.max_cost_per_hour_usd == 1.0

    def test_default_config_values(self, tmp_path):
        """Default config should match documented defaults."""
        cfg = RateLimitConfig()
        assert cfg.max_tool_calls_per_minute == 30
        assert cfg.max_agent_launches_per_hour == 20
        assert cfg.max_bash_commands_per_minute == 15
        assert cfg.max_file_writes_per_minute == 10
        assert cfg.max_cost_per_hour_usd == 5.0
        assert cfg.cooldown_seconds == 60


# ---------------------------------------------------------------------------
# format_status
# ---------------------------------------------------------------------------


class TestFormatStatus:
    """format_status should produce human-readable output."""

    def test_format_status_includes_all_types(self, tmp_path):
        """Formatted status should mention all action types and cost."""
        rl = _make_limiter(tmp_path)
        output = rl.format_status()
        assert "tool_call" in output
        assert "agent_launch" in output
        assert "bash_command" in output
        assert "file_write" in output
        assert "cost" in output
        assert "remaining" in output

    def test_format_status_shows_used_counts(self, tmp_path):
        """Formatted status should reflect actual usage."""
        rl = _make_limiter(tmp_path, max_tool_calls_per_minute=10)
        rl.record("tool_call")
        rl.record("tool_call")
        output = rl.format_status()
        assert "2/10" in output


# ---------------------------------------------------------------------------
# Cooldown behavior
# ---------------------------------------------------------------------------


class TestCooldown:
    """After being blocked, actions should be allowed once window expires."""

    def test_allowed_after_window_expires(self, tmp_path):
        """After entries age out past the window, new calls should be allowed."""
        rl = _make_limiter(tmp_path, max_tool_calls_per_minute=2)
        # Inject entries that are old enough to be cleaned
        old_time = time.time() - 120
        rl.state.tool_calls = [old_time, old_time + 1]
        rl._save_state()

        # Now check should pass because old entries are cleaned
        allowed, _ = rl.check("tool_call")
        assert allowed is True


# ---------------------------------------------------------------------------
# RateLimitState
# ---------------------------------------------------------------------------


class TestRateLimitState:
    """State serialization and list accessor."""

    def test_to_dict_roundtrip(self):
        """State should survive dict serialization."""
        state = RateLimitState(
            tool_calls=[1.0, 2.0],
            agent_launches=[3.0],
            bash_commands=[],
            file_writes=[4.0, 5.0],
            cost_usd=1.23,
            cost_reset_at=9999.0,
        )
        restored = RateLimitState.from_dict(state.to_dict())
        assert restored.tool_calls == [1.0, 2.0]
        assert restored.agent_launches == [3.0]
        assert restored.file_writes == [4.0, 5.0]
        assert abs(restored.cost_usd - 1.23) < 0.001
        assert restored.cost_reset_at == 9999.0

    def test_from_dict_with_missing_keys(self):
        """from_dict should handle missing keys gracefully."""
        state = RateLimitState.from_dict({})
        assert state.tool_calls == []
        assert state.cost_usd == 0.0
        assert state.cost_reset_at is None
