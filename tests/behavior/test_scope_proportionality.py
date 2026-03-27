"""Behavior tests for hooks/scope-proportionality.sh

Validates the scope proportionality check: fix tasks with deletes,
fix tasks with many files, refactor tasks, and non-Agent tool bypass.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = PROJECT_ROOT / "hooks" / "scope-proportionality.sh"


def run_hook(
    tool_name: str,
    task_desc: str,
    response: str,
    phase: str = "reconstruction",
    env_extra: dict = None,
) -> subprocess.CompletedProcess:
    """Run the scope-proportionality hook with simulated input."""
    stdin_data = json.dumps({
        "tool_name": tool_name,
        "tool_input": {"prompt": task_desc},
        "tool_response": response,
    })

    env = os.environ.copy()
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    env["COGNITIVE_OS_SESSION_ID"] = ""

    # Create a temp project dir for the hook to write metrics
    import tempfile
    tmpdir = tempfile.mkdtemp()
    cos_dir = os.path.join(tmpdir, ".cognitive-os", "metrics")
    os.makedirs(cos_dir, exist_ok=True)

    # Write a minimal cognitive-os.yaml with the desired phase
    config_path = os.path.join(tmpdir, "cognitive-os.yaml")
    with open(config_path, "w") as f:
        f.write("project:\n  phase: %s\n" % phase)

    env["CLAUDE_PROJECT_DIR"] = tmpdir
    env["COGNITIVE_OS_PROJECT_DIR"] = tmpdir

    if env_extra:
        env.update(env_extra)

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=stdin_data,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


class TestScopeProportionality:
    """Tests for the scope-proportionality PostToolUse hook."""

    def test_fix_task_no_deletes_passes(self):
        """Fix task with only modifications should pass (exit 0)."""
        response = "modified file src/handler.go\nmodified file src/handler_test.go"
        result = run_hook("Agent", "fix the null pointer bug in handler", response)
        assert result.returncode == 0

    def test_fix_task_with_deletes_blocks_in_production(self):
        """Fix task with file deletions should BLOCK in production phase."""
        response = (
            "modified file src/handler.go\n"
            "deleted file src/old_handler.go\n"
            "removed file src/legacy.go"
        )
        result = run_hook(
            "Agent",
            "fix the null pointer bug in handler",
            response,
            phase="production",
        )
        assert result.returncode == 2
        assert "BLOCK" in result.stderr

    def test_fix_task_with_deletes_warns_in_reconstruction(self):
        """Fix task with file deletions should WARN (not block) in reconstruction."""
        response = (
            "modified file src/handler.go\n"
            "deleted file src/old_handler.go"
        )
        result = run_hook(
            "Agent",
            "fix the null pointer bug in handler",
            response,
            phase="reconstruction",
        )
        assert result.returncode == 0
        assert "WARNING" in result.stderr or "WARN" in result.stderr.upper()

    def test_fix_task_many_files_warns(self):
        """Fix task touching >20 files should warn."""
        lines = ["modified file src/file_%d.go" % i for i in range(25)]
        response = "\n".join(lines)
        result = run_hook("Agent", "fix the config loading bug", response)
        assert result.returncode == 0
        assert "disproportionate" in result.stderr.lower() or "WARNING" in result.stderr

    def test_refactor_task_with_deletes_passes(self):
        """Refactor task with file deletions is proportional and should pass."""
        response = (
            "modified file src/handler.go\n"
            "deleted file src/old_handler.go\n"
            "created file src/new_handler.go"
        )
        result = run_hook("Agent", "refactor the handler module", response)
        assert result.returncode == 0

    def test_non_agent_tool_ignored(self):
        """Non-Agent tools should be silently ignored (exit 0)."""
        result = run_hook("Bash", "fix the bug", "deleted everything")
        assert result.returncode == 0

    def test_any_task_many_deletes_warns(self):
        """Any task deleting >5 files should warn."""
        lines = ["deleted file src/file_%d.go" % i for i in range(8)]
        response = "\n".join(lines)
        result = run_hook("Agent", "refactor the entire module", response)
        assert result.returncode == 0
        assert "deleted" in result.stderr.lower() or "WARN" in result.stderr.upper()
