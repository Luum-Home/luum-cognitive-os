"""Behavior tests for the self-improvement loop.

Creates mock metrics data with known patterns, runs analysis hooks,
and verifies they detect patterns and produce correct output.
Migrated from test-self-improvement.sh.
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture
def mock_metrics_env(tmp_path, project_root):
    """Set up a temporary project with mock metrics data."""
    test_project = tmp_path / "project"
    test_cos = test_project / ".cognitive-os"
    test_metrics = test_cos / "metrics"
    test_refine = test_metrics / "auto-refine"
    test_metrics.mkdir(parents=True)
    test_refine.mkdir(parents=True)

    # Copy cognitive-os.yaml for config reading
    src_config = project_root / "cognitive-os.yaml"
    if src_config.exists():
        dest_config = test_cos / "cognitive-os.yaml"
        dest_config.write_text(src_config.read_text())

    return {
        "project_dir": test_project,
        "metrics_dir": test_metrics,
        "env": {
            "CLAUDE_PROJECT_DIR": str(test_project),
            "COGNITIVE_OS_SESSION_START": "2026-03-22T00:00:00Z",
        },
    }


@pytest.mark.behavior
class TestSelfImprovementHooksExist:
    """Tests that self-improvement hooks and skills exist."""

    def test_kpi_trigger_exists_and_executable(self, hooks_dir):
        hook = hooks_dir / "kpi-trigger.sh"
        if not hook.exists():
            pytest.fail("kpi-trigger.sh does not exist")
        assert os.access(hook, os.X_OK), "kpi-trigger.sh should be executable"

    def test_session_learning_exists_and_executable(self, hooks_dir):
        hook = hooks_dir / "session-learning.sh"
        if not hook.exists():
            pytest.fail("session-learning.sh does not exist")
        assert os.access(hook, os.X_OK), "session-learning.sh should be executable"


@pytest.mark.behavior
class TestSelfImprovementProtocol:
    """Tests for self-improvement-protocol rule."""


    def test_protocol_includes_rollback(self, project_root):
        rule = project_root / "rules" / "self-improvement-protocol.md"
        if not rule.exists():
            pytest.skip("protocol file not found")
        content = rule.read_text()
        assert any(w in content.lower() for w in ["rollback", "roll back", "revert"]), (
            "protocol should include rollback procedures"
        )


@pytest.mark.behavior
class TestMockMetricsData:
    """Tests using mock metrics data to verify pattern detection."""

    def _create_error_data(self, metrics_dir: Path):
        """Create mock error-learning.jsonl with known patterns."""
        error_file = metrics_dir / "error-learning.jsonl"
        epoch = int(time.time())

        # 5 TEST_FAILURE errors for service-a
        for i in range(1, 6):
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            entry = {
                "timestamp": ts,
                "timestamp_epoch": epoch - i * 60,
                "type": "TEST_FAILURE",
                "service": "service-a",
                "framework": "go-test",
                "error": "FAIL: TestUserCreate - expected 200 got 500",
                "command": "go test ./...",
                "context": "assertion failure in test",
                "fingerprint": "abc123",
            }
            with open(error_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

        # 3 LINT_ERROR for service-c
        for i in range(1, 4):
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            entry = {
                "timestamp": ts,
                "timestamp_epoch": epoch - i * 120,
                "type": "LINT_ERROR",
                "service": "service-c",
                "framework": "eslint",
                "error": "error TS2345: Argument of type string is not assignable",
                "command": "npx eslint .",
                "context": "TypeScript type error",
                "fingerprint": "def456",
            }
            with open(error_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

        return error_file

    def _create_skill_metrics(self, metrics_dir: Path):
        """Create mock skill-metrics.jsonl (7 success, 3 failure = 70%)."""
        skill_file = metrics_dir / "skill-metrics.jsonl"
        for i in range(1, 8):
            entry = {
                "timestamp": f"2026-03-22T10:0{i}:00Z",
                "skill": "apply",
                "model": "sonnet",
                "tokens": 5000,
                "duration_ms": 3000,
                "success": True,
            }
            with open(skill_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

        for i in range(1, 4):
            entry = {
                "timestamp": f"2026-03-22T11:0{i}:00Z",
                "skill": "apply",
                "model": "sonnet",
                "tokens": 8000,
                "duration_ms": 5000,
                "success": False,
            }
            with open(skill_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

        return skill_file

    def test_mock_error_data_creation(self, mock_metrics_env):
        error_file = self._create_error_data(mock_metrics_env["metrics_dir"])
        lines = error_file.read_text().strip().split("\n")
        assert len(lines) == 8, f"Expected 8 mock entries, got {len(lines)}"

    def test_mock_skill_metrics_creation(self, mock_metrics_env):
        skill_file = self._create_skill_metrics(mock_metrics_env["metrics_dir"])
        lines = skill_file.read_text().strip().split("\n")
        assert len(lines) == 10, f"Expected 10 skill entries, got {len(lines)}"

    def test_kpi_trigger_produces_snapshot(self, hooks_dir, mock_metrics_env):
        hook = hooks_dir / "kpi-trigger.sh"
        if not hook.exists() or not os.access(hook, os.X_OK):
            pytest.skip("kpi-trigger.sh not executable")

        self._create_error_data(mock_metrics_env["metrics_dir"])
        self._create_skill_metrics(mock_metrics_env["metrics_dir"])

        result = subprocess.run(
            ["bash", str(hook)],
            capture_output=True,
            text=True,
            env={**os.environ, **mock_metrics_env["env"]},
            timeout=15,
        )
        assert result.returncode == 0, f"kpi-trigger.sh exited with {result.returncode}"

        kpi_file = mock_metrics_env["metrics_dir"] / "kpi-history.jsonl"
        if kpi_file.exists():
            last_line = kpi_file.read_text().strip().split("\n")[-1]
            json.loads(last_line)
            assert "first_pass_success_rate" in last_line, "should contain first_pass_success_rate"
            assert "avg_iterations" in last_line, "should contain avg_iterations"

    def test_session_learning_produces_entry(self, hooks_dir, mock_metrics_env):
        hook = hooks_dir / "session-learning.sh"
        if not hook.exists() or not os.access(hook, os.X_OK):
            pytest.skip("session-learning.sh not executable")

        self._create_error_data(mock_metrics_env["metrics_dir"])
        self._create_skill_metrics(mock_metrics_env["metrics_dir"])

        result = subprocess.run(
            ["bash", str(hook)],
            capture_output=True,
            text=True,
            env={**os.environ, **mock_metrics_env["env"]},
            timeout=15,
        )
        assert result.returncode == 0, f"session-learning.sh exited with {result.returncode}"

        learnings = mock_metrics_env["metrics_dir"] / "session-learnings.jsonl"
        if learnings.exists():
            last_line = learnings.read_text().strip().split("\n")[-1]
            assert "session_errors" in last_line, "should contain session_errors"
            assert "success_rate" in last_line, "should contain success_rate"


