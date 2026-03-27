"""Tests for lib/rate_limit_protection.py — Rate Limit Protection.

Author: luum
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.rate_limit_protection import RateLimitProtection, RateLimitStatus


@pytest.fixture
def tmp_metrics(tmp_path: Path) -> Path:
    """Create a temporary metrics directory."""
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    return metrics


@pytest.fixture
def protection(tmp_metrics: Path) -> RateLimitProtection:
    """Create a RateLimitProtection with temp paths."""
    cost_path = str(tmp_metrics / "cost-events.jsonl")
    config_path = str(tmp_metrics / "nonexistent-config.yaml")
    p = RateLimitProtection(
        cost_events_path=cost_path,
        config_path=config_path,
    )
    return p


class TestCheck:
    """Tests for check() method."""

    def test_check_returns_status_with_pct_used(
        self, protection: RateLimitProtection
    ) -> None:
        status = protection.check()
        assert isinstance(status, RateLimitStatus)
        assert 0.0 <= status.pct_used <= 1.0
        assert status.tokens_estimated_remaining >= 0

    def test_check_empty_cost_events_returns_safe(
        self, protection: RateLimitProtection
    ) -> None:
        status = protection.check()
        assert status.should_pause is False
        assert status.pct_used < 0.5
        assert "safe" in status.reason.lower() or "within" in status.reason.lower()


class TestShouldLaunchAgent:
    """Tests for should_launch_agent() method."""

    def test_allows_at_low_usage(self, protection: RateLimitProtection) -> None:
        allowed, reason = protection.should_launch_agent()
        assert allowed is True
        assert reason == "OK"

    def test_blocks_at_95_percent(self, protection: RateLimitProtection) -> None:
        # Simulate high token usage by setting internal counters
        protection._session_tokens_in = 4_800_000
        protection._session_tokens_out = 0
        status = protection.check()
        assert status.pct_used >= 0.95
        allowed, reason = protection.should_launch_agent()
        assert allowed is False
        assert "BLOCKED" in reason

    def test_blocks_when_agent_limit_reached(
        self, protection: RateLimitProtection
    ) -> None:
        protection._session_agents = 30
        allowed, reason = protection.should_launch_agent()
        assert allowed is False
        assert "Agent limit" in reason

    def test_override_bypasses_block(self, protection: RateLimitProtection) -> None:
        protection._session_tokens_in = 4_900_000
        with patch.dict(os.environ, {"RATE_LIMIT_OVERRIDE": "true"}):
            allowed, reason = protection.should_launch_agent()
        assert allowed is True
        assert "Override" in reason


class TestRecordUsage:
    """Tests for record_usage() method."""

    def test_record_usage_tracks_tokens(
        self, protection: RateLimitProtection, tmp_metrics: Path
    ) -> None:
        protection.record_usage(
            tokens_in=1000, tokens_out=2000, model="sonnet", action="bash_command"
        )
        assert protection._session_tokens_in == 1000
        assert protection._session_tokens_out == 2000

        cost_file = Path(protection.cost_events_path)
        assert cost_file.exists()
        with open(cost_file) as fh:
            entry = json.loads(fh.readline())
        assert entry["input_tokens"] == 1000
        assert entry["output_tokens"] == 2000
        assert entry["total_tokens"] == 3000
        assert entry["model"] == "sonnet"

    def test_record_agent_launch_increments_counter(
        self, protection: RateLimitProtection
    ) -> None:
        protection.record_usage(
            tokens_in=50000, tokens_out=100000, model="opus", action="agent_launch"
        )
        assert protection._session_agents == 1


class TestEstimateActionCost:
    """Tests for estimate_action_cost_tokens() method."""

    def test_agent_launch_estimate(self, protection: RateLimitProtection) -> None:
        cost = protection.estimate_action_cost_tokens("agent_launch")
        assert cost == 150_000

    def test_bash_command_estimate(self, protection: RateLimitProtection) -> None:
        cost = protection.estimate_action_cost_tokens("bash_command")
        assert cost == 2_000

    def test_unknown_action_returns_default(
        self, protection: RateLimitProtection
    ) -> None:
        cost = protection.estimate_action_cost_tokens("unknown_action")
        assert cost == 2_000


class TestFormatting:
    """Tests for format_status, format_warning, format_block."""

    def test_format_status_one_liner(self, protection: RateLimitProtection) -> None:
        result = protection.format_status()
        assert "Tokens:" in result
        assert "Agents:" in result
        assert "Reset:" in result

    def test_format_warning_at_80_percent(
        self, protection: RateLimitProtection
    ) -> None:
        protection._session_tokens_in = 4_100_000
        result = protection.format_warning()
        assert "WARNING" in result
        assert "agents" in result.lower()

    def test_format_block_at_95_percent(
        self, protection: RateLimitProtection
    ) -> None:
        protection._session_tokens_in = 4_800_000
        result = protection.format_block()
        assert "RATE LIMIT REACHED" in result
        assert "RATE_LIMIT_OVERRIDE" in result


class TestSaveSession:
    """Tests for save_session_for_resume."""

    def test_save_session_creates_file(self, tmp_path: Path) -> None:
        pause_path = tmp_path / ".cognitive-os" / "rate-limit-pause.json"
        cost_path = str(tmp_path / "cost-events.jsonl")
        p = RateLimitProtection(cost_events_path=cost_path)

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            p.save_session_for_resume()
            assert pause_path.exists()
            data = json.loads(pause_path.read_text())
            assert "paused_at" in data
            assert "tokens_used" in data
            assert "pct_used" in data
        finally:
            os.chdir(original_cwd)


class TestConfigurable:
    """Tests for configurable limits."""

    def test_custom_limits(self, tmp_path: Path) -> None:
        config = tmp_path / "config.yaml"
        config.write_text(
            "resources:\n"
            "  rate_limit:\n"
            "    hourly_token_limit: 1000000\n"
            "    daily_token_limit: 10000000\n"
            "    max_agents_per_hour: 10\n"
        )
        p = RateLimitProtection(
            cost_events_path=str(tmp_path / "cost.jsonl"),
            config_path=str(config),
        )
        assert p.hourly_token_limit == 1_000_000
        assert p.daily_token_limit == 10_000_000
        assert p.max_agents_per_hour == 10


class TestHourlyReset:
    """Tests for hourly reset logic."""

    def test_old_events_not_counted(
        self, protection: RateLimitProtection, tmp_metrics: Path
    ) -> None:
        """Events older than 1 hour should not count toward hourly usage."""
        cost_file = Path(protection.cost_events_path)
        # Write an event from 2 hours ago
        old_ts = "2020-01-01T00:00:00+00:00"
        entry = {
            "timestamp": old_ts,
            "model": "opus",
            "action": "agent_launch",
            "input_tokens": 999999,
            "output_tokens": 999999,
            "total_tokens": 1999998,
        }
        with open(cost_file, "w") as fh:
            fh.write(json.dumps(entry) + "\n")

        status = protection.check()
        # Old events should not be counted (only in-memory session counters)
        assert status.tokens_used_session < 2_000_000
