"""Edge matrix for ADR-101 intent-aware rate limiter behavior."""

from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path

import pytest

import lib.rate_limiter as rate_limiter_module
from lib.rate_limiter import RateLimitConfig, RateLimiter, RateLimitQueue

pytestmark = pytest.mark.unit

HOOK_PATH = Path(__file__).resolve().parent.parent.parent / "hooks" / "rate-limiter.sh"
DRAIN_HOOK_PATH = (
    Path(__file__).resolve().parent.parent.parent / "hooks" / "rate-limit-drain.sh"
)


def _limiter(tmp_path: Path, **overrides) -> RateLimiter:
    return RateLimiter(
        config=RateLimitConfig(**overrides),
        state_path=str(tmp_path / "state.json"),
        phase="stabilization",
    )


def _run_hook(project_dir: Path, payload: dict, env: dict | None = None):
    hook_env = os.environ.copy()
    hook_env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    hook_env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    hook_env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    if env:
        hook_env.update(env)
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=hook_env,
        timeout=15,
    )


def _run_drainer(project_dir: Path, env: dict | None = None):
    hook_env = os.environ.copy()
    hook_env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    hook_env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    hook_env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    if env:
        hook_env.update(env)
    return subprocess.run(
        ["bash", str(DRAIN_HOOK_PATH)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {}}),
        capture_output=True,
        text=True,
        env=hook_env,
        timeout=15,
    )


def _write_rate_config(project_dir: Path, body: str) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "cognitive-os.yaml").write_text(
        "project:\n  phase: stabilization\nsecurity:\n  rate_limits:\n" + body
    )


class TestTokenBucketRefillEdges:
    """Boundary tests for bucket initialization, depletion, and refill."""

    def test_bucket_refills_with_controlled_clock(self, tmp_path, monkeypatch):
        """A depleted bucket should refill according to elapsed wall time."""
        now = 1_000.0
        monkeypatch.setattr(rate_limiter_module.time, "time", lambda: now)
        rl = _limiter(
            tmp_path,
            max_bash_commands_per_minute=6,
            burst_multiplier=1.0,
            operator_reserve_ratio=0.0,
        )

        for _ in range(6):
            assert rl.check("bash_command")[0] is True
            rl.record("bash_command")

        blocked, _ = rl.check("bash_command")
        assert blocked is False

        now = 1_030.0
        allowed, reason = rl.check("bash_command")

        assert allowed is True, reason
        assert rl.get_status()["bash_command"]["bucket_tokens"] == 3.0

    def test_old_signature_events_expire_before_penalty(self, tmp_path, monkeypatch):
        """Loop penalty should ignore signatures outside the action window."""
        now = 10_000.0
        monkeypatch.setattr(rate_limiter_module.time, "time", lambda: now)
        rl = _limiter(
            tmp_path,
            max_bash_commands_per_minute=10,
            burst_multiplier=1.0,
            operator_reserve_ratio=0.0,
            diversity_penalty_min_events=5,
        )
        for _ in range(5):
            rl.record("bash_command", signature="same")

        now = 10_061.0
        assert rl._diversity_penalty_active("bash_command", "same") is False

    def test_malformed_bucket_and_signature_state_recovers(self, tmp_path):
        """Malformed persisted bucket/signature payloads should not crash."""
        state = tmp_path / "state.json"
        state.write_text(
            json.dumps(
                {
                    "buckets": {"bash_command": "bad"},
                    "action_signatures": {"bash_command": "bad"},
                    "bash_commands": [1, 2],
                }
            )
        )

        rl = RateLimiter(state_path=str(state), phase="stabilization")
        allowed, reason = rl.check("bash_command", signature="abc")

        assert allowed is True, reason
        status = rl.get_status()["bash_command"]
        assert status["burst_capacity"] >= 1


class TestRateLimitConfigEdges:
    """Config parser edge cases for security.rate_limits."""

    def test_config_ignores_unknown_keys_and_preserves_defaults(self, tmp_path):
        """Unknown config keys should not affect defaults or crash."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "security:\n"
            "  rate_limits:\n"
            "    max_bash_commands_per_minute: 7\n"
            "    unknown_future_knob: 123\n"
        )

        rl = RateLimiter(state_path=str(tmp_path / "state.json"), config_path=str(config))

        assert rl.config.max_bash_commands_per_minute == 7
        assert rl.config.max_tool_calls_per_minute == 30
        assert not hasattr(rl.config, "unknown_future_knob")

    def test_config_block_stops_at_parent_indent(self, tmp_path):
        """Parser should not absorb sibling YAML keys after rate_limits."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "security:\n"
            "  rate_limits:\n"
            "    max_bash_commands_per_minute: 7\n"
            "other:\n"
            "  burst_multiplier: 99\n"
        )

        rl = RateLimiter(state_path=str(tmp_path / "state.json"), config_path=str(config))

        assert rl.config.max_bash_commands_per_minute == 7
        assert rl.config.burst_multiplier == 1.5

    def test_invalid_config_values_are_ignored_individually(self, tmp_path):
        """Bad scalar/range values should fall back without poisoning valid keys."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "security:\n"
            "  rate_limits:\n"
            "    max_bash_commands_per_minute: nope\n"
            "    max_tool_calls_per_minute: -5\n"
            "    burst_multiplier: 0\n"
            "    warning_threshold: 1.5\n"
            "    cooldown_seconds: -1\n"
            "    operator_reserve_ratio: false\n"
            "    max_file_writes_per_minute: 6\n"
        )

        rl = RateLimiter(state_path=str(tmp_path / "state.json"), config_path=str(config))

        assert rl.config.max_bash_commands_per_minute == 15
        assert rl.config.max_tool_calls_per_minute == 30
        assert rl.config.burst_multiplier == 1.5
        assert rl.config.warning_threshold == 0.80
        assert rl.config.cooldown_seconds == 60
        assert rl.config.operator_reserve_ratio == 0.20
        assert rl.config.max_file_writes_per_minute == 6

    def test_partial_config_applies_valid_subset(self, tmp_path):
        """A partial rate_limits block should override only listed valid keys."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "security:\n"
            "  rate_limits:\n"
            "    max_agent_launches_per_hour: 3\n"
            "    cooldown_seconds: 0\n"
        )

        rl = RateLimiter(state_path=str(tmp_path / "state.json"), config_path=str(config))

        assert rl.config.max_agent_launches_per_hour == 3
        assert rl.config.cooldown_seconds == 0
        assert rl.config.max_bash_commands_per_minute == 15


class TestLegacyStateCompatibilityEdges:
    """Backward compatibility for pre-ADR-101 persisted rate-limit state."""

    def test_legacy_state_without_buckets_or_signatures_is_accepted(self, tmp_path):
        """Old state files with only timestamp lists should initialize buckets."""
        state = tmp_path / "state.json"
        state.write_text(
            json.dumps(
                {
                    "tool_calls": [1.0],
                    "agent_launches": [],
                    "bash_commands": [1.0, 2.0],
                    "file_writes": [],
                    "cost_usd": 0.25,
                    "cost_reset_at": 9_999_999_999.0,
                }
            )
        )

        rl = RateLimiter(state_path=str(state), phase="stabilization")
        allowed, reason = rl.check("bash_command")
        rl.record("bash_command", signature="new-command")
        persisted = json.loads(state.read_text())

        assert allowed is True, reason
        assert "buckets" in persisted
        assert "action_signatures" in persisted
        assert persisted["bash_commands"][-1] >= persisted["bash_commands"][0]
        assert persisted["cost_usd"] == 0.25

    def test_realistic_legacy_exhausted_state_can_still_block(self, tmp_path):
        """Legacy count history should not hide an already depleted bucket state."""
        state = tmp_path / "state.json"
        state.write_text(
            json.dumps(
                {
                    "tool_calls": [],
                    "agent_launches": [],
                    "bash_commands": [],
                    "file_writes": [],
                    "buckets": {
                        "bash_command": {"tokens": 0.0, "updated_at": 9_999_999_999.0}
                    },
                    "cost_usd": 0.0,
                    "cost_reset_at": 9_999_999_999.0,
                }
            )
        )

        rl = RateLimiter(
            config=RateLimitConfig(
                max_bash_commands_per_minute=1,
                burst_multiplier=1.0,
                operator_reserve_ratio=0.0,
            ),
            state_path=str(state),
            phase="stabilization",
        )

        allowed, reason = rl.check("bash_command")

        assert allowed is False
        assert "token bucket" in reason


class TestConcurrentStateEdges:
    """Concurrency smoke tests for persisted rate state."""

    def test_concurrent_recorders_preserve_all_events(self, tmp_path):
        """Concurrent records should not corrupt state or lose updates."""
        state = tmp_path / "state.json"
        errors: list[Exception] = []

        def worker() -> None:
            try:
                rl = RateLimiter(state_path=str(state), phase="stabilization")
                for _ in range(20):
                    rl.record("tool_call")
            except Exception as exc:  # pragma: no cover - failure path assertion
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
        loaded = json.loads(state.read_text())
        assert isinstance(loaded, dict)
        assert isinstance(loaded.get("tool_calls"), list)
        assert len(loaded["tool_calls"]) == 120


class TestRateLimiterHookEdges:
    """Hook-level edge coverage for ADR-101 warning and priority behavior."""

    def test_hook_emits_soft_warning_without_blocking(self, tmp_path):
        """Crossing warning_threshold should print RATE_LIMIT_WARNING and exit 0."""
        _write_rate_config(
            tmp_path,
            "    max_bash_commands_per_minute: 4\n"
            "    burst_multiplier: 1.0\n"
            "    warning_threshold: 0.45\n"
            "    operator_reserve_ratio: 0.0\n",
        )
        payload = {"tool_name": "Bash", "tool_input": {"command": "echo warning"}}

        first = _run_hook(tmp_path, payload)
        second = _run_hook(tmp_path, payload)

        assert first.returncode == 0
        assert second.returncode == 0
        assert "RATE_LIMIT_WARNING:" in second.stderr

    def test_hook_priority_lane_override_preserves_operator_reserve(self, tmp_path):
        """Normal lane should block at reserve while operator override passes."""
        _write_rate_config(
            tmp_path,
            "    max_bash_commands_per_minute: 4\n"
            "    burst_multiplier: 1.0\n"
            "    operator_reserve_ratio: 0.25\n",
        )
        state = tmp_path / ".cognitive-os" / "rate-limit-state.json"
        rl = RateLimiter(
            state_path=str(state),
            config_path=str(tmp_path / "cognitive-os.yaml"),
            phase="stabilization",
        )
        for i in range(3):
            rl.record("bash_command", signature=f"prefill-{i}")

        payload = {"tool_name": "Bash", "tool_input": {"command": "echo lane"}}
        normal = _run_hook(
            tmp_path,
            payload,
            env={"COS_RATE_LIMIT_PRIORITY_LANE": "normal"},
        )
        operator = _run_hook(
            tmp_path,
            payload,
            env={"COS_RATE_LIMIT_PRIORITY_LANE": "operator"},
        )

        assert normal.returncode == 2
        assert "operator reserve protected" in normal.stderr
        assert operator.returncode == 0, operator.stderr

    def test_hook_disable_env_skips_existing_block(self, tmp_path):
        """DISABLE_HOOK_RATE_LIMITER should bypass an otherwise blocked state."""
        _write_rate_config(
            tmp_path,
            "    max_bash_commands_per_minute: 1\n"
            "    burst_multiplier: 1.0\n"
            "    operator_reserve_ratio: 0.0\n",
        )
        payload = {"tool_name": "Bash", "tool_input": {"command": "echo disabled"}}
        assert _run_hook(tmp_path, payload).returncode == 0
        assert _run_hook(tmp_path, payload).returncode == 2

        disabled = _run_hook(
            tmp_path,
            payload,
            env={"DISABLE_HOOK_RATE_LIMITER": "true"},
        )

        assert disabled.returncode == 0
        assert disabled.stderr == ""


class TestRateLimiterEndToEndEdges:
    """End-to-end block → queue → drain → retry behavior with token buckets."""

    def test_block_queue_drain_retry_executes_after_bucket_recovers(self, tmp_path):
        """A blocked safe Bash command should be queued, drained, and executed."""
        _write_rate_config(
            tmp_path,
            "    max_bash_commands_per_minute: 1\n"
            "    burst_multiplier: 1.0\n"
            "    cooldown_seconds: 0\n"
            "    operator_reserve_ratio: 0.0\n",
        )
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "echo e2e_retry_ok"},
        }

        first = _run_hook(tmp_path, payload)
        blocked = _run_hook(tmp_path, payload)

        assert first.returncode == 0, first.stderr
        assert blocked.returncode == 2, blocked.stderr
        assert "RATE_LIMIT_QUEUED" in blocked.stderr

        queue = RateLimitQueue(
            state_path=str(tmp_path / ".cognitive-os" / "rate-limit-queue.json"),
            cooldown_seconds=0,
        )
        queued = queue.peek()
        assert len(queued) == 1
        assert queued[0]["context"]["command"] == "echo e2e_retry_ok"

        RateLimiter(
            state_path=str(tmp_path / ".cognitive-os" / "rate-limit-state.json"),
            config_path=str(tmp_path / "cognitive-os.yaml"),
            phase="stabilization",
        ).reset()

        drained = _run_drainer(tmp_path)

        assert drained.returncode == 0, drained.stderr
        assert "RATE_LIMIT_EXECUTED" in drained.stderr
        executed_log = tmp_path / ".cognitive-os" / "rate-limit-executed.jsonl"
        records = [
            json.loads(line)
            for line in executed_log.read_text().splitlines()
            if line.strip()
        ]
        assert records[-1]["command"] == "echo e2e_retry_ok"
        assert records[-1]["exit_code"] == 0
        assert "e2e_retry_ok" in records[-1]["stdout_snippet"]
        assert RateLimitQueue(
            state_path=str(tmp_path / ".cognitive-os" / "rate-limit-queue.json"),
            cooldown_seconds=0,
        ).peek() == []
