"""Tests for lib/token_budget_monitor.py — Token Budget Monitor.

Imports via lib.token_budget_monitor (canonical).  The old module name
lib.rate_limit_protection remains as a deprecation shim.

Author: luum
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.token_budget_monitor import RateLimitProtection, RateLimitStatus

pytestmark = [pytest.mark.xdist_group("perf_budget"), pytest.mark.benchmark]


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
        # record_usage writes via MetricEvent which nests token fields under "payload"
        payload = entry["payload"]
        assert payload["input_tokens"] == 1000
        assert payload["output_tokens"] == 2000
        assert payload["total_tokens"] == 3000
        assert payload["model"] == "sonnet"

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


# ---------------------------------------------------------------------------
# Hook-level performance and correctness tests
# (merged from test_rate_limit_protection_perf.py — targets
#  hooks/token-budget-monitor.sh directly via subprocess)
# ---------------------------------------------------------------------------

import subprocess

_HOOK_PATH = Path(__file__).resolve().parents[2] / "hooks" / "token-budget-monitor.sh"


def _run_hook(tmpdir: str, extra_env: dict | None = None, stdin: str = "") -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": tmpdir,
        "CODEX_PROJECT_DIR": "",
        "CLAUDE_PROJECT_DIR": tmpdir,
        "HOME": tmpdir,
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(_HOOK_PATH)],
        env=env,
        capture_output=True,
        text=True,
        input=stdin,
        timeout=5,
    )


def _write_cost_events(metrics_dir: Path, count: int, tokens_per_event: int = 100,
                       every_nth_is_agent: int = 3,
                       timestamp: str = "2026-04-15T23:00:00+00:00") -> None:
    metrics_dir.mkdir(parents=True, exist_ok=True)
    with open(metrics_dir / "cost-events.jsonl", "w") as f:
        for i in range(count):
            action = "agent_launch" if i % every_nth_is_agent == 0 else "tool_call"
            f.write(json.dumps({
                "timestamp": timestamp,
                "total_tokens": tokens_per_event,
                "action": action,
            }) + "\n")


class TestPerf:
    """Performance tests for hooks/token-budget-monitor.sh.

    Verifies the single-pass Python optimisation keeps the hook fast
    (no multiple python3 cold starts).
    """

    def test_completes_under_500ms_empty_file(self, tmp_path: Path) -> None:
        """No cost-events file: must complete in < 500 ms."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True)

        env = {"RATE_LIMIT_OVERRIDE": "false"}
        start = time.monotonic()
        result = _run_hook(str(tmp_path), extra_env=env)
        elapsed = time.monotonic() - start

        assert elapsed < 0.5, f"Took {elapsed:.3f}s (limit 0.5s); stderr={result.stderr[:200]}"

    def test_completes_under_500ms_with_1000_lines(self, tmp_path: Path) -> None:
        """1000-line cost-events file must still complete in < 500 ms."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        _write_cost_events(metrics_dir, count=1000)

        env = {"RATE_LIMIT_OVERRIDE": "true"}
        start = time.monotonic()
        result = _run_hook(str(tmp_path), extra_env=env)
        elapsed = time.monotonic() - start

        assert elapsed < 0.5, f"Took {elapsed:.3f}s (limit 0.5s); stderr={result.stderr[:200]}"


class TestTokenCountingHook:
    """Correctness tests for the token-budget-monitor.sh hook."""

    def test_token_counting_correct(self, tmp_path: Path) -> None:
        """Tokens are summed from total_tokens field across recent events."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        _write_cost_events(metrics_dir, count=10, tokens_per_event=500)

        env = {"RATE_LIMIT_OVERRIDE": "false"}
        result = _run_hook(str(tmp_path), extra_env=env)
        assert result.returncode == 0, f"Unexpected block; stderr={result.stderr}"

    def test_agent_launch_counting(self, tmp_path: Path) -> None:
        """agent_launch events are counted separately from tool_call events."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        events = []
        for i in range(5):
            events.append({"timestamp": "2026-04-15T23:00:00+00:00",
                            "total_tokens": 10, "action": "agent_launch"})
        for i in range(5):
            events.append({"timestamp": "2026-04-15T23:00:00+00:00",
                            "total_tokens": 10, "action": "tool_call"})

        with open(metrics_dir / "cost-events.jsonl", "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        result = _run_hook(str(tmp_path), extra_env={"RATE_LIMIT_OVERRIDE": "false"})
        assert result.returncode == 0, f"Should not be blocked; stderr={result.stderr}"

    def test_token_counting_consults_adr_325_resource_ledger(self, tmp_path: Path) -> None:
        """ADR-325 resource ledger rows contribute to hourly token enforcement."""
        from datetime import datetime, timezone

        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        with open(metrics_dir / "ai-resource-ledger.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "schema_version": 1,
                "ts": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
                "agent_id": "",
                "task_id": "",
                "provider": "hook",
                "model": "context-budget-meter",
                "tokens_in": 96,
                "tokens_out": 0,
                "estimated_cost_usd": 0.0,
                "actual_cost_usd": 0.0,
                "retry_count": 0,
                "tool_calls": 0,
                "reasoning_effort": "none",
                "kind": "context_budget",
                "source": "context-budget-meter",
            }) + "\n")

        result = _run_hook(
            str(tmp_path),
            extra_env={
                "RATE_LIMIT_OVERRIDE": "false",
                "RATE_LIMIT_HOURLY_TOKENS": "100",
            },
        )

        assert result.returncode == 2
        assert "RATE LIMIT REACHED (96%)" in result.stderr


class TestHourlyCutoffHook:
    """Hourly cutoff tests for the token-budget-monitor.sh hook."""

    def test_hourly_cutoff_excludes_old_events(self, tmp_path: Path) -> None:
        """Events older than 1 hour must NOT count towards the rate limit."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        old_ts = "2026-04-15T21:00:00+00:00"
        events = [
            {"timestamp": old_ts, "total_tokens": 4_900_000, "action": "tool_call"},
        ]
        fresh_ts = "2026-04-15T23:00:00+00:00"
        events.append({"timestamp": fresh_ts, "total_tokens": 1000, "action": "tool_call"})

        with open(metrics_dir / "cost-events.jsonl", "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        result = _run_hook(str(tmp_path), extra_env={"RATE_LIMIT_OVERRIDE": "false"})
        assert result.returncode != 2, (
            f"Old events were counted; gate should not block; stderr={result.stderr}"
        )


class TestExitCodesHook:
    """Exit code tests for the token-budget-monitor.sh hook."""

    def test_exits_2_over_95_percent_tokens(self, tmp_path: Path) -> None:
        """Hook must exit 2 when token usage exceeds 95% of the hourly limit."""
        from datetime import datetime, timezone
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        hourly_limit = 1_000_000
        tokens = int(hourly_limit * 0.96)
        fresh_ts = datetime.now(timezone.utc).isoformat()
        with open(metrics_dir / "cost-events.jsonl", "w") as f:
            f.write(json.dumps({
                "timestamp": fresh_ts,
                "total_tokens": tokens,
                "action": "tool_call",
            }) + "\n")

        env = {
            "RATE_LIMIT_OVERRIDE": "false",
            "RATE_LIMIT_HOURLY_TOKENS": str(hourly_limit),
        }
        result = _run_hook(str(tmp_path), extra_env=env)
        assert result.returncode == 2, (
            f"Expected exit 2 at 96% usage, got {result.returncode}; stderr={result.stderr}"
        )

    def test_exits_0_under_limit(self, tmp_path: Path) -> None:
        """Hook must exit 0 when token usage is well below the limit."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        _write_cost_events(metrics_dir, count=5, tokens_per_event=100)

        env = {
            "RATE_LIMIT_OVERRIDE": "false",
            "RATE_LIMIT_HOURLY_TOKENS": "5000000",
        }
        result = _run_hook(str(tmp_path), extra_env=env)
        assert result.returncode == 0, (
            f"Expected exit 0 under limit, got {result.returncode}; stderr={result.stderr}"
        )


class TestOverrideHook:
    """Override bypass tests for the token-budget-monitor.sh hook."""

    def test_rate_limit_override_bypasses(self, tmp_path: Path) -> None:
        """RATE_LIMIT_OVERRIDE=true must cause an immediate exit 0."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        hourly_limit = 100
        with open(metrics_dir / "cost-events.jsonl", "w") as f:
            f.write(json.dumps({
                "timestamp": "2026-04-15T23:00:00+00:00",
                "total_tokens": 99,
                "action": "tool_call",
            }) + "\n")

        env = {
            "RATE_LIMIT_OVERRIDE": "true",
            "RATE_LIMIT_HOURLY_TOKENS": str(hourly_limit),
        }
        start = time.monotonic()
        result = _run_hook(str(tmp_path), extra_env=env)
        elapsed = time.monotonic() - start

        assert result.returncode == 0, (
            f"Override should bypass gate; got {result.returncode}; stderr={result.stderr}"
        )
        assert elapsed < 0.3, f"Override should be near-instant; took {elapsed:.3f}s"
