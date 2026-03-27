"""Behavior tests for private mode.

Tests private-mode-gate.sh and private-mode-metrics-gate.sh flag behavior.
Migrated from test-private-mode.sh.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

PRIVATE_MODE_FLAG = "/tmp/claude-private-mode-active"


@pytest.fixture(autouse=True)
def cleanup_flag():
    """Ensure the private-mode flag is removed before and after each test."""
    if os.path.exists(PRIVATE_MODE_FLAG):
        os.unlink(PRIVATE_MODE_FLAG)
    yield
    if os.path.exists(PRIVATE_MODE_FLAG):
        os.unlink(PRIVATE_MODE_FLAG)


@pytest.fixture
def gate_hook(project_root):
    hook = project_root / ".cognitive-os" / "hooks" / "private-mode-gate.sh"
    if not hook.exists() or not os.access(hook, os.X_OK):
        pytest.skip("private-mode-gate.sh not found or not executable")
    return hook


@pytest.fixture
def metrics_gate_hook(project_root):
    hook = project_root / ".cognitive-os" / "hooks" / "private-mode-metrics-gate.sh"
    if not hook.exists() or not os.access(hook, os.X_OK):
        pytest.skip("private-mode-metrics-gate.sh not found or not executable")
    return hook


def _run_gate(hook_path, project_root, mock_input):
    return subprocess.run(
        ["bash", str(hook_path)],
        input=mock_input,
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project_root)},
        timeout=10,
    )


@pytest.mark.behavior
class TestPrivateMode:
    """Tests for private mode gate behavior."""

    def test_gate_allows_when_flag_absent(self, gate_hook, project_root):
        mock = json.dumps({"tool_name": "mem_save", "tool_input": {"title": "test"}})
        result = _run_gate(gate_hook, project_root, mock)
        assert result.returncode == 0, "should exit 0 when flag absent"
        output = (result.stdout + result.stderr).lower()
        assert "deny" not in output, "should NOT deny engram when flag absent"

    def test_gate_blocks_when_flag_present(self, gate_hook, project_root):
        Path(PRIVATE_MODE_FLAG).touch()
        mock = json.dumps({"tool_name": "mem_save", "tool_input": {"title": "test"}})
        result = _run_gate(gate_hook, project_root, mock)
        assert result.returncode == 0, "should exit 0 (graceful deny)"
        output = (result.stdout + result.stderr).lower()
        assert "deny" in output, "should deny engram in private mode"

    def test_metrics_gate_passes_in_normal_mode(self, metrics_gate_hook, project_root):
        mock = json.dumps({"tool_name": "Bash", "tool_input": {"command": "test"}})
        result = _run_gate(metrics_gate_hook, project_root, mock)
        assert result.returncode == 0, "metrics gate should exit 0 in normal mode"

    def test_metrics_gate_suppresses_in_private_mode(self, metrics_gate_hook, project_root):
        Path(PRIVATE_MODE_FLAG).touch()
        mock = json.dumps({"tool_name": "Bash", "tool_input": {"command": "test"}})
        result = _run_gate(metrics_gate_hook, project_root, mock)
        assert result.returncode == 0, "metrics gate should exit 0 in private mode"
