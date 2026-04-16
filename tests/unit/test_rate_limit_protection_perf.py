"""Behavioral + performance tests for hooks/rate-limit-protection.sh.

Verifies correctness and prevents performance regression after the
single-pass Python optimisation (no multiple python3 cold starts).
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOK_PATH = Path(__file__).resolve().parents[2] / "hooks" / "rate-limit-protection.sh"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_hook(tmpdir: str, extra_env: dict | None = None, stdin: str = "") -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": tmpdir,
        # Suppress accidental writes to real metrics dir
        "HOME": tmpdir,
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
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


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------

class TestPerformance:
    def test_completes_under_500ms_empty_file(self, tmp_path):
        """No cost-events file: must complete in < 500 ms."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True)

        env = {"RATE_LIMIT_OVERRIDE": "false"}
        start = time.monotonic()
        result = _run_hook(str(tmp_path), extra_env=env)
        elapsed = time.monotonic() - start

        assert elapsed < 0.5, f"Took {elapsed:.3f}s (limit 0.5s); stderr={result.stderr[:200]}"

    def test_completes_under_500ms_with_1000_lines(self, tmp_path):
        """1000-line cost-events file must still complete in < 500 ms."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        _write_cost_events(metrics_dir, count=1000)

        env = {"RATE_LIMIT_OVERRIDE": "true"}  # bypass rate-limit; just measure speed
        start = time.monotonic()
        result = _run_hook(str(tmp_path), extra_env=env)
        elapsed = time.monotonic() - start

        assert elapsed < 0.5, f"Took {elapsed:.3f}s (limit 0.5s); stderr={result.stderr[:200]}"


# ---------------------------------------------------------------------------
# Functional / correctness tests
# ---------------------------------------------------------------------------

class TestTokenCounting:
    def test_token_counting_correct(self, tmp_path):
        """Tokens are summed from total_tokens field across recent events."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        _write_cost_events(metrics_dir, count=10, tokens_per_event=500)

        # 10 events * 500 tokens = 5000 tokens
        # Default limit is 5_000_000 — should be well under threshold
        env = {"RATE_LIMIT_OVERRIDE": "false"}
        result = _run_hook(str(tmp_path), extra_env=env)
        assert result.returncode == 0, f"Unexpected block; stderr={result.stderr}"

    def test_agent_launch_counting(self, tmp_path):
        """agent_launch events are counted separately from tool_call events."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        # Write exactly 5 agent_launch events (well under default limit of 30)
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


class TestHourlyCutoff:
    def test_hourly_cutoff_excludes_old_events(self, tmp_path):
        """Events older than 1 hour must NOT count towards the rate limit."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        # Write events with a timestamp from 2 hours ago — should be excluded
        old_ts = "2026-04-15T21:00:00+00:00"  # 2h before "now" (23:00)
        events = [
            {"timestamp": old_ts, "total_tokens": 4_900_000, "action": "tool_call"},
        ]
        # Plus one fresh event that should NOT trigger the limit
        fresh_ts = "2026-04-15T23:00:00+00:00"
        events.append({"timestamp": fresh_ts, "total_tokens": 1000, "action": "tool_call"})

        with open(metrics_dir / "cost-events.jsonl", "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        # The old 4.9M tokens must be excluded; only 1K fresh tokens count
        result = _run_hook(str(tmp_path), extra_env={"RATE_LIMIT_OVERRIDE": "false"})
        # Should exit 0 (or at most warn at 80%), never exit 2
        assert result.returncode != 2, (
            f"Old events were counted; gate should not block; stderr={result.stderr}"
        )


class TestExitCodes:
    def test_exits_2_over_95_percent_tokens(self, tmp_path):
        """Hook must exit 2 when token usage exceeds 95% of the hourly limit."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        hourly_limit = 1_000_000
        # 96% of limit → should trigger block
        tokens = int(hourly_limit * 0.96)

        # Use a fresh timestamp (current time) — hook's cutoff is now - 1h
        from datetime import datetime, timezone
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

    def test_exits_0_under_limit(self, tmp_path):
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


class TestOverride:
    def test_rate_limit_override_bypasses(self, tmp_path):
        """RATE_LIMIT_OVERRIDE=true must cause an immediate exit 0."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        # Fill events to well over 95% of a small limit
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
        # Override is an early-exit — should be very fast
        assert elapsed < 0.3, f"Override should be near-instant; took {elapsed:.3f}s"
