"""Shared fixtures for behavior tests."""

import os
import subprocess
import shutil
import json
from pathlib import Path
from typing import Optional

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def project_root() -> Path:
    """Return the absolute path to the project root."""
    return PROJECT_ROOT


@pytest.fixture
def hooks_dir(project_root: Path) -> Path:
    """Return the absolute path to the hooks directory."""
    return project_root / "hooks"


@pytest.fixture
def skills_dir(project_root: Path) -> Path:
    """Return the absolute path to the skills directory."""
    return project_root / "skills"


@pytest.fixture
def run_hook(hooks_dir: Path):
    """Return a helper function to run a hook script.

    Usage:
        result = run_hook("my-hook.sh", env={"VAR": "val"}, stdin='{"key": "val"}')
        assert result.returncode == 0
    """

    def _run_hook(
        hook_name: str,
        env: Optional[dict] = None,
        stdin: Optional[str] = None,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess:
        hook_path = hooks_dir / hook_name
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        return subprocess.run(
            ["bash", str(hook_path)],
            input=stdin,
            capture_output=True,
            text=True,
            env=run_env,
            timeout=timeout,
        )

    return _run_hook


@pytest.fixture
def cognitive_os_env(tmp_path: Path):
    """Set up a temporary cognitive-os project directory structure.

    Returns a dict with environment variables and paths commonly needed by hooks.
    """
    project_dir = tmp_path / "project"
    session_id = f"test-session-{os.getpid()}"
    cos_dir = project_dir / ".cognitive-os"

    # Create standard directory structure
    for subdir in [
        "metrics",
        "tasks",
        "sessions",
        "checkpoints",
        "transcripts",
        f"sessions/{session_id}/metrics",
        "rules",
        "skills",
        "squads",
        "agents",
        "templates",
        "workflows",
    ]:
        (cos_dir / subdir).mkdir(parents=True, exist_ok=True)

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
