"""Unit tests for lib/rate_limiter.py

Validates rate limiting logic: check/record/status/reset/cleanup,
cost tracking, state persistence, custom configs, phase-aware limits,
and edge cases.
"""

import math
import time

import pytest

from lib.rate_limiter import (
    VALID_ACTIONS,
    RateLimitConfig,
    RateLimiter,
    RateLimitState,
    _read_phase_from_config,
    get_phase_modifier,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_limiter(tmp_path, phase="stabilization", **config_overrides):
    """Create a RateLimiter with a temp state file and optional config.

    Defaults to stabilization phase (1.0x modifier) so existing tests
    behave identically to pre-phase-awareness behavior.
    """
    cfg = RateLimitConfig(**config_overrides)
    return RateLimiter(
        config=cfg, state_path=str(tmp_path / "state.json"), phase=phase
    )


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

    def test_blocks_tool_calls_when_bucket_and_reserve_exhausted(self, tmp_path):
        """Should block when burst bucket reaches the normal-lane reserve."""
        rl = _make_limiter(tmp_path, max_tool_calls_per_minute=3)
        normal_capacity = math.floor(
            rl.burst_capacity("tool_call") * (1 - rl.config.operator_reserve_ratio)
        )
        for _ in range(normal_capacity):
            rl.record("tool_call")
        allowed, reason = rl.check("tool_call")
        assert allowed is False
        assert "tool_call" in reason
        assert "token bucket" in reason.lower()

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
        assert status["tool_call"]["remaining"] == 10
        assert status["tool_call"]["used"] == 2
        assert status["tool_call"]["limit"] == 10
        assert status["tool_call"]["burst_capacity"] == 15

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
            phase="stabilization",
        )
        rl1.record("tool_call")
        rl1.record("tool_call")
        rl1.record("agent_launch", cost_usd=0.5)

        # New instance loading from same path
        rl2 = RateLimiter(
            config=RateLimitConfig(max_tool_calls_per_minute=50),
            state_path=state_path,
            phase="stabilization",
        )
        status = rl2.get_status()
        assert status["tool_call"]["used"] == 2
        assert status["agent_launch"]["used"] == 1

    def test_load_from_nonexistent_creates_fresh(self, tmp_path):
        """Loading from a non-existent file should create fresh state."""
        rl = RateLimiter(
            state_path=str(tmp_path / "nope.json"), phase="stabilization"
        )
        status = rl.get_status()
        for action in VALID_ACTIONS:
            assert status[action]["used"] == 0

    def test_load_from_corrupted_file_creates_fresh(self, tmp_path):
        """Loading from a corrupted JSON file should create fresh state."""
        state_file = tmp_path / "state.json"
        state_file.write_text("not valid json {{{")
        rl = RateLimiter(
            state_path=str(state_file), phase="stabilization"
        )
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

    def test_format_status_shows_phase(self, tmp_path):
        """Formatted status should include the current phase."""
        rl = _make_limiter(tmp_path, phase="production")
        output = rl.format_status()
        assert "production" in output
        assert "0.75x" in output


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


# ---------------------------------------------------------------------------
# Phase-aware rate limiting
# ---------------------------------------------------------------------------


class TestPhaseAwareness:
    """Phase modifiers should scale limits correctly."""

    def test_phase_property(self, tmp_path):
        """RateLimiter should expose the resolved phase."""
        rl = _make_limiter(tmp_path, phase="reconstruction")
        assert rl.phase == "reconstruction"

    def test_phase_modifier_property(self, tmp_path):
        """RateLimiter should expose the modifier for introspection."""
        rl = _make_limiter(tmp_path, phase="reconstruction")
        assert rl.phase_modifier == 1.5

    def test_reconstruction_increases_limits(self, tmp_path):
        """Reconstruction phase (1.5x) should allow more actions."""
        # Base agent_launch limit is 20, with 1.5x = 30
        rl = _make_limiter(tmp_path, phase="reconstruction")
        assert rl.effective_limit("agent_launch") == 30
        assert rl.effective_limit("tool_call") == 45  # 30 * 1.5
        assert rl.effective_limit("bash_command") == 22  # floor(15 * 1.5)
        assert rl.effective_limit("file_write") == 15  # 10 * 1.5

    def test_stabilization_keeps_base_limits(self, tmp_path):
        """Stabilization phase (1.0x) should use base limits unchanged."""
        rl = _make_limiter(tmp_path, phase="stabilization")
        assert rl.effective_limit("agent_launch") == 20
        assert rl.effective_limit("tool_call") == 30
        assert rl.effective_limit("bash_command") == 15
        assert rl.effective_limit("file_write") == 10

    def test_production_reduces_limits(self, tmp_path):
        """Production phase (0.75x) should restrict limits."""
        rl = _make_limiter(tmp_path, phase="production")
        assert rl.effective_limit("agent_launch") == 15  # floor(20 * 0.75)
        assert rl.effective_limit("tool_call") == 22  # floor(30 * 0.75)
        assert rl.effective_limit("bash_command") == 11  # floor(15 * 0.75)
        assert rl.effective_limit("file_write") == 7  # floor(10 * 0.75)

    def test_maintenance_halves_limits(self, tmp_path):
        """Maintenance phase (0.5x) should halve all limits."""
        rl = _make_limiter(tmp_path, phase="maintenance")
        assert rl.effective_limit("agent_launch") == 10  # 20 * 0.5
        assert rl.effective_limit("tool_call") == 15  # 30 * 0.5
        assert rl.effective_limit("bash_command") == 7  # floor(15 * 0.5)
        assert rl.effective_limit("file_write") == 5  # 10 * 0.5

    def test_unknown_phase_defaults_to_1x(self, tmp_path):
        """Unknown phase should default to 1.0x (stabilization-equivalent)."""
        rl = _make_limiter(tmp_path, phase="unknown_phase")
        assert rl.phase_modifier == 1.0
        assert rl.effective_limit("agent_launch") == 20

    def test_reconstruction_allows_more_before_blocking(self, tmp_path):
        """In reconstruction, 25 agent launches should be allowed (limit=30)."""
        rl = _make_limiter(tmp_path, phase="reconstruction")
        for _ in range(25):
            rl.record("agent_launch")
        allowed, _ = rl.check("agent_launch")
        assert allowed is True, "reconstruction should allow up to 30 agent launches"

    def test_reconstruction_blocks_after_burst_capacity(self, tmp_path):
        """In reconstruction, burst capacity applies before normal-lane block."""
        rl = _make_limiter(tmp_path, phase="reconstruction")
        normal_capacity = math.floor(
            rl.burst_capacity("agent_launch") * (1 - rl.config.operator_reserve_ratio)
        )
        for _ in range(normal_capacity):
            rl.record("agent_launch")
        allowed, reason = rl.check("agent_launch")
        assert allowed is False
        assert "reconstruction" in reason

    def test_production_blocks_earlier(self, tmp_path):
        """Production has lower refill and burst capacity than stabilization."""
        rl = _make_limiter(tmp_path, phase="production")
        normal_capacity = math.floor(
            rl.burst_capacity("agent_launch") * (1 - rl.config.operator_reserve_ratio)
        )
        for _ in range(normal_capacity):
            rl.record("agent_launch")
        allowed, reason = rl.check("agent_launch")
        assert allowed is False
        assert "production" in reason

    def test_cost_cap_is_phase_adjusted(self, tmp_path):
        """Cost cap should also be adjusted by phase modifier."""
        # Base cost cap is 5.0, reconstruction = 5.0 * 1.5 = 7.5
        rl = _make_limiter(tmp_path, phase="reconstruction")
        rl.record("tool_call", cost_usd=6.0)
        allowed, _ = rl.check("tool_call")
        assert allowed is True, "6.0 < 7.5 effective cost cap in reconstruction"

        rl2 = _make_limiter(tmp_path, phase="production")
        rl2.record("tool_call", cost_usd=4.0)
        allowed2, reason2 = rl2.check("tool_call")
        assert allowed2 is False, "4.0 >= 3.75 effective cost cap in production"
        assert "cost cap" in reason2.lower()

    def test_status_includes_phase_info(self, tmp_path):
        """get_status should include phase and modifier."""
        rl = _make_limiter(tmp_path, phase="reconstruction")
        status = rl.get_status()
        assert status["phase"] == "reconstruction"
        assert status["phase_modifier"] == 1.5

    def test_status_shows_effective_limits(self, tmp_path):
        """get_status limits should reflect phase-adjusted values."""
        rl = _make_limiter(tmp_path, phase="maintenance")
        status = rl.get_status()
        assert status["agent_launch"]["limit"] == 10  # 20 * 0.5
        assert status["agent_launch"]["base_limit"] == 20

    def test_effective_limit_never_zero(self, tmp_path):
        """Effective limit should be at least 1, even with tiny modifiers."""
        cfg = RateLimitConfig(max_file_writes_per_minute=1)
        rl = RateLimiter(
            config=cfg,
            state_path=str(tmp_path / "state.json"),
            phase="maintenance",  # 0.5x
        )
        # floor(1 * 0.5) = 0 but max(1, ...) ensures at least 1
        assert rl.effective_limit("file_write") == 1

    def test_block_reason_includes_phase_context(self, tmp_path):
        """Block reason should mention phase and modifier for debuggability."""
        rl = _make_limiter(tmp_path, phase="production", max_tool_calls_per_minute=4)
        normal_capacity = math.floor(
            rl.burst_capacity("tool_call") * (1 - rl.config.operator_reserve_ratio)
        )
        for _ in range(normal_capacity):
            rl.record("tool_call")
        allowed, reason = rl.check("tool_call")
        assert allowed is False
        assert "production" in reason
        assert "0.75" in reason

    def test_operator_lane_can_use_reserved_tokens(self, tmp_path):
        """Operator lane may consume tokens preserved from normal orchestrator work."""
        rl = _make_limiter(tmp_path, max_bash_commands_per_minute=4)
        normal_capacity = math.floor(
            rl.burst_capacity("bash_command") * (1 - rl.config.operator_reserve_ratio)
        )
        for _ in range(normal_capacity):
            rl.record("bash_command")

        normal_allowed, _ = rl.check("bash_command")
        operator_allowed, _ = rl.check("bash_command", priority_lane="operator")

        assert normal_allowed is False
        assert operator_allowed is True

    def test_repeated_signature_penalty_blocks_before_diverse_work(self, tmp_path):
        """Repeated identical command signatures consume extra tokens as a loop signal."""
        rl_loop = _make_limiter(tmp_path / "loop", max_bash_commands_per_minute=6)
        signature = "same-command"
        for _ in range(6):
            rl_loop.record("bash_command", signature=signature)

        loop_allowed, loop_reason = rl_loop.check("bash_command", signature=signature)

        rl_diverse = _make_limiter(tmp_path / "diverse", max_bash_commands_per_minute=6)
        for i in range(6):
            rl_diverse.record("bash_command", signature=f"cmd-{i}")

        diverse_allowed, _ = rl_diverse.check("bash_command", signature="cmd-new")

        assert loop_allowed is False
        assert "diversity penalty" in loop_reason
        assert diverse_allowed is True


# ---------------------------------------------------------------------------
# Phase config reading
# ---------------------------------------------------------------------------


class TestPhaseConfigReading:
    """Phase should be read from cognitive-os.yaml when not provided."""

    def test_reads_phase_from_yaml(self, tmp_path):
        """Should parse phase from a cognitive-os.yaml file."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("project:\n  name: test\n  phase: production\n")
        phase = _read_phase_from_config(str(config))
        assert phase == "production"

    def test_reads_reconstruction_phase(self, tmp_path):
        """Should correctly read 'reconstruction' phase."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("  phase: reconstruction  # comment\n")
        phase = _read_phase_from_config(str(config))
        assert phase == "reconstruction"

    def test_missing_config_defaults_to_stabilization(self, tmp_path, monkeypatch):
        """Missing config should default to stabilization (1.0x)."""
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        phase = _read_phase_from_config(str(tmp_path / "nonexistent.yaml"))
        assert phase == "stabilization"

    def test_config_without_phase_defaults(self, tmp_path, monkeypatch):
        """Config file without phase key should default to stabilization."""
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("project:\n  name: test\n")
        phase = _read_phase_from_config(str(config))
        assert phase == "stabilization"

    def test_get_phase_modifier_for_all_phases(self):
        """get_phase_modifier should return correct values for all phases."""
        assert get_phase_modifier("reconstruction") == 1.5
        assert get_phase_modifier("stabilization") == 1.0
        assert get_phase_modifier("production") == 0.75
        assert get_phase_modifier("maintenance") == 0.5

    def test_get_phase_modifier_unknown_defaults_to_1(self):
        """Unknown phase should return 1.0."""
        assert get_phase_modifier("imaginary") == 1.0

    def test_limiter_uses_config_file(self, tmp_path, monkeypatch):
        """RateLimiter should read phase from config when not passed."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("  phase: maintenance\n")
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)

        rl = RateLimiter(
            state_path=str(tmp_path / "state.json"),
            config_path=str(config),
        )
        assert rl.phase == "maintenance"
        assert rl.phase_modifier == 0.5


    def test_limiter_reads_rate_limit_config(self, tmp_path, monkeypatch):
        """RateLimiter should read security.rate_limits overrides from config."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "security:\n"
            "  rate_limits:\n"
            "    max_bash_commands_per_minute: 4\n"
            "    burst_multiplier: 2.0\n"
            "    operator_reserve_ratio: 0.25\n"
        )
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)

        rl = RateLimiter(
            state_path=str(tmp_path / "state.json"),
            config_path=str(config),
            phase="stabilization",
        )

        assert rl.config.max_bash_commands_per_minute == 4
        assert rl.config.burst_multiplier == 2.0
        assert rl.config.operator_reserve_ratio == 0.25
        assert rl.burst_capacity("bash_command") == 8

    def test_limiter_env_var_lookup(self, tmp_path, monkeypatch):
        """RateLimiter should find config via CLAUDE_PROJECT_DIR env var."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("  phase: production\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        rl = RateLimiter(
            state_path=str(tmp_path / "state.json"),
        )
        assert rl.phase == "production"
        assert rl.phase_modifier == 0.75


# ---------------------------------------------------------------------------
# Bug fix: blocked attempts should NOT be recorded
# ---------------------------------------------------------------------------


class TestBlockedAttemptNotRecorded:
    """Blocked attempts must not inflate the rate limit counter.

    The rate-limiter.sh hook previously called record() unconditionally
    before checking if the action was allowed. This caused blocked attempts
    to count toward the limit, making the rate limit progressively worse.

    Fix: record() should only be called when check() returns allowed=True.
    """

    def test_blocked_attempt_not_recorded(self, tmp_path):
        """When check() returns blocked, count should not increase.

        Simulates the corrected hook behavior: only call record() when
        allowed. Verifies that a blocked check does not inflate counters.
        """
        rl = _make_limiter(tmp_path, max_agent_launches_per_hour=2)
        # Fill to the limit
        rl.record("agent_launch")
        rl.record("agent_launch")
        status_before = rl.get_status()
        assert status_before["agent_launch"]["used"] == 2

        # Simulate the corrected hook: check first, only record if allowed
        allowed, reason = rl.check("agent_launch")
        assert allowed is False  # Should be blocked

        # Do NOT call record() since check returned blocked
        status_after = rl.get_status()
        assert status_after["agent_launch"]["used"] == 2, (
            "Blocked attempt should NOT increase the counter"
        )

    def test_allowed_attempt_recorded(self, tmp_path):
        """When check() returns allowed, record() should increase count.

        Simulates the corrected hook behavior: check -> record on success.
        """
        rl = _make_limiter(tmp_path, max_agent_launches_per_hour=5)
        status_before = rl.get_status()
        assert status_before["agent_launch"]["used"] == 0

        # Simulate the corrected hook: check first, then record
        allowed, reason = rl.check("agent_launch")
        assert allowed is True

        rl.record("agent_launch")
        status_after = rl.get_status()
        assert status_after["agent_launch"]["used"] == 1, (
            "Allowed attempt should increase the counter after record()"
        )
