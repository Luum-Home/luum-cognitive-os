"""Behavior tests for hook trigger behavior.

Migrated from test-hook-triggers.sh.
Simulates tool events and verifies hooks produce expected output.
Tests: inject-phase-context, error-learning, resource-check, tool-loop-detector.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

import pytest

pytestmark = pytest.mark.behavior


def _hooks_dir() -> Path:
    """Return the .cognitive-os/hooks directory under the project."""
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / ".cognitive-os" / "hooks"


@pytest.fixture
def cos_hooks_dir():
    """Return the .cognitive-os/hooks directory."""
    d = _hooks_dir()
    if not d.exists():
        pytest.skip(".cognitive-os/hooks directory not found")
    return d


@pytest.fixture
def project_dir_env():
    """Return environment dict with CLAUDE_PROJECT_DIR set to actual project root."""
    project_root = Path(__file__).resolve().parent.parent.parent
    return {"CLAUDE_PROJECT_DIR": str(project_root)}


def run_cos_hook(
    hooks_dir: Path,
    hook_name: str,
    env: Optional[dict] = None,
    stdin: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Run a hook from the .cognitive-os/hooks directory."""
    hook_path = hooks_dir / hook_name
    if not hook_path.exists():
        pytest.skip(f"{hook_name} not found")
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        ["bash", str(hook_path)],
        input=stdin,
        capture_output=True,
        text=True,
        env=run_env,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# 1. inject-phase-context.sh
# ---------------------------------------------------------------------------


class TestInjectPhaseContext:

    def test_exits_0_for_agent_tool(self, cos_hooks_dir, project_dir_env):
        hook = cos_hooks_dir / "inject-phase-context.sh"
        if not hook.exists():
            pytest.skip("inject-phase-context.sh not found")
        if not os.access(str(hook), os.X_OK):
            pytest.skip("inject-phase-context.sh not executable")

        mock_input = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "test prompt"},
        })
        result = run_cos_hook(cos_hooks_dir, "inject-phase-context.sh", env=project_dir_env, stdin=mock_input)
        assert result.returncode == 0


    def test_outputs_valid_phase_name(self, cos_hooks_dir, project_dir_env):
        hook = cos_hooks_dir / "inject-phase-context.sh"
        if not hook.exists() or not os.access(str(hook), os.X_OK):
            pytest.skip("inject-phase-context.sh not available")

        mock_input = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "test prompt"},
        })
        result = run_cos_hook(cos_hooks_dir, "inject-phase-context.sh", env=project_dir_env, stdin=mock_input)
        combined = (result.stdout + result.stderr).lower()
        valid_phases = ("reconstruction", "stabilization", "production", "maintenance")
        assert any(phase in combined for phase in valid_phases)


    def test_no_output_for_non_agent(self, cos_hooks_dir, project_dir_env):
        hook = cos_hooks_dir / "inject-phase-context.sh"
        if not hook.exists() or not os.access(str(hook), os.X_OK):
            pytest.skip("inject-phase-context.sh not available")

        mock_input = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        result = run_cos_hook(cos_hooks_dir, "inject-phase-context.sh", env=project_dir_env, stdin=mock_input)
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# 2. error-learning.sh
# ---------------------------------------------------------------------------


class TestErrorLearning:

    def test_exits_0_on_simulated_failure(self, cos_hooks_dir, project_dir_env):
        hook = cos_hooks_dir / "error-learning.sh"
        if not hook.exists() or not os.access(str(hook), os.X_OK):
            pytest.skip("error-learning.sh not available")

        mock_fail = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "go test ./..."},
            "tool_response": "FAIL: TestSomething - expected 1 got 2",
            "exit_code": "1",
        })
        result = run_cos_hook(cos_hooks_dir, "error-learning.sh", env=project_dir_env, stdin=mock_fail)
        assert result.returncode == 0

    def test_ignores_successful_commands(self, cos_hooks_dir, project_dir_env):
        hook = cos_hooks_dir / "error-learning.sh"
        if not hook.exists() or not os.access(str(hook), os.X_OK):
            pytest.skip("error-learning.sh not available")

        project_root = Path(__file__).resolve().parent.parent.parent
        metrics_file = project_root / ".cognitive-os" / "metrics" / "error-learning.jsonl"
        lines_before = 0
        if metrics_file.exists():
            lines_before = len(metrics_file.read_text().strip().splitlines())

        mock_success = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "go test ./..."},
            "tool_response": "ok",
            "exit_code": "0",
        })
        run_cos_hook(cos_hooks_dir, "error-learning.sh", env=project_dir_env, stdin=mock_success)

        lines_after = 0
        if metrics_file.exists():
            lines_after = len(metrics_file.read_text().strip().splitlines())
        assert lines_after == lines_before


# ---------------------------------------------------------------------------
# 3. resource-check.sh
# ---------------------------------------------------------------------------


class TestResourceCheck:

    def test_exits_0_with_no_cost_data(self, cos_hooks_dir, project_dir_env):
        hook = cos_hooks_dir / "resource-check.sh"
        if not hook.exists() or not os.access(str(hook), os.X_OK):
            pytest.skip("resource-check.sh not available")

        mock_agent = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "do something"},
        })
        result = run_cos_hook(cos_hooks_dir, "resource-check.sh", env=project_dir_env, stdin=mock_agent)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 4. tool-loop-detector.sh
# ---------------------------------------------------------------------------


class TestToolLoopDetector:

    def test_exits_0_on_normal_usage(self, cos_hooks_dir, project_dir_env):
        hook = cos_hooks_dir / "tool-loop-detector.sh"
        if not hook.exists() or not os.access(str(hook), os.X_OK):
            pytest.skip("tool-loop-detector.sh not available")

        mock_input = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "echo hello"},
            "tool_response": "hello",
        })
        result = run_cos_hook(cos_hooks_dir, "tool-loop-detector.sh", env=project_dir_env, stdin=mock_input)
        assert result.returncode == 0
