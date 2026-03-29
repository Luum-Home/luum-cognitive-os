"""Shared fixtures for hook shell-level tests.

These tests invoke hooks via subprocess with mock JSON stdin,
verifying exit codes, JSON parsing, and graceful degradation.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = PROJECT_ROOT / "hooks"


@pytest.fixture
def hooks_dir() -> Path:
    """Return the absolute path to the hooks directory."""
    return HOOKS_DIR


@pytest.fixture
def run_hook():
    """Run a hook with mock stdin JSON and return CompletedProcess.

    Usage:
        result = run_hook("rate-limiter.sh", stdin_json={...}, env={...})
        assert result.returncode == 0
    """

    def _run(
        hook_name: str,
        stdin_json: Optional[dict] = None,
        stdin_text: Optional[str] = None,
        env: Optional[dict] = None,
        timeout: int = 15,
    ) -> subprocess.CompletedProcess:
        hook_path = HOOKS_DIR / hook_name
        if not hook_path.exists():
            pytest.skip(f"Hook {hook_name} not found")

        run_env = os.environ.copy()
        # Always set a project dir pointing to a temp or real location
        if env:
            run_env.update(env)

        if stdin_text is not None:
            stdin_str = stdin_text
        elif stdin_json is not None:
            stdin_str = json.dumps(stdin_json)
        else:
            stdin_str = ""

        return subprocess.run(
            ["bash", str(hook_path)],
            input=stdin_str,
            capture_output=True,
            text=True,
            env=run_env,
            timeout=timeout,
        )

    return _run


@pytest.fixture
def mock_project(tmp_path):
    """Create a minimal mock project directory with cognitive-os structure.

    Returns a dict with paths and env vars needed by hooks.
    """
    project_dir = tmp_path / "project"
    cos_dir = project_dir / ".cognitive-os"
    session_id = f"test-{os.getpid()}"

    for subdir in [
        "metrics",
        "tasks",
        "sessions",
        f"sessions/{session_id}/metrics",
        "checkpoints",
        "rules",
    ]:
        (cos_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Create minimal cognitive-os.yaml
    config = cos_dir / "cognitive-os.yaml"
    config.write_text(
        "project:\n"
        "  name: test-project\n"
        "  phase: reconstruction\n"
        "model_capability:\n"
        "  level: 3\n"
        "security:\n"
        "  rate_limits:\n"
        "    max_tool_calls_per_minute: 30\n"
        "    max_agent_launches_per_hour: 20\n"
        "    max_bash_commands_per_minute: 15\n"
        "    max_file_writes_per_minute: 10\n"
        "    max_cost_per_hour_usd: 5.0\n"
        "    cooldown_seconds: 60\n"
    )

    # Also create a root-level cognitive-os.yaml (some hooks check both)
    root_config = project_dir / "cognitive-os.yaml"
    root_config.write_text(config.read_text())

    # Init a git repo so hooks that use git rev-parse work
    subprocess.run(
        ["git", "init", "-q"],
        cwd=str(project_dir),
        capture_output=True,
    )

    env = {
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_SESSION_ID": session_id,
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
    }

    return {
        "env": env,
        "project_dir": project_dir,
        "cos_dir": cos_dir,
        "session_id": session_id,
    }


@pytest.fixture
def private_mode():
    """Activate private mode for the duration of a test."""
    flag = Path("/tmp/claude-private-mode-active")
    flag.touch()
    yield flag
    flag.unlink(missing_ok=True)


def make_agent_input(prompt: str = "Test task") -> dict:
    """Build a mock Agent tool input JSON."""
    return {
        "tool_name": "Agent",
        "tool_input": {"prompt": prompt},
    }


def make_agent_response(prompt: str = "Test", response: str = "Done") -> dict:
    """Build a mock Agent PostToolUse JSON with response."""
    return {
        "tool_name": "Agent",
        "tool_input": {"prompt": prompt},
        "tool_response": response,
    }


def make_edit_input(
    file_path: str = "/tmp/test.py",
    old_string: str = "old",
    new_string: str = "new",
) -> dict:
    """Build a mock Edit tool input JSON."""
    return {
        "tool_name": "Edit",
        "tool_input": {
            "file_path": file_path,
            "old_string": old_string,
            "new_string": new_string,
        },
    }


def make_write_input(file_path: str = "/tmp/test.py", content: str = "hello") -> dict:
    """Build a mock Write tool input JSON."""
    return {
        "tool_name": "Write",
        "tool_input": {
            "file_path": file_path,
            "content": content,
        },
    }


def make_bash_input(command: str = "echo hello") -> dict:
    """Build a mock Bash tool input JSON."""
    return {
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


def make_bash_response(
    command: str = "echo hello",
    response: str = "hello",
    exit_code: str = "0",
) -> dict:
    """Build a mock Bash PostToolUse JSON with response."""
    return {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": response,
        "exit_code": exit_code,
    }
