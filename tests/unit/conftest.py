"""Shared fixtures for unit tests that call bash library functions."""
import json
import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def lib_dir(project_root) -> Path:
    """Return the path to hooks/_lib/ directory."""
    return project_root / "hooks" / "_lib"


@pytest.fixture
def helpers_dir(project_root) -> Path:
    """Return the path to tests/_helpers/ directory."""
    return project_root / "tests" / "_helpers"


def run_bash_function(lib_path: str, function_name: str, *args, env: "dict | None" = None) -> subprocess.CompletedProcess:
    """Source a bash library file and call a function from it.

    Args:
        lib_path: Absolute path to the bash library to source.
        function_name: Name of the bash function to call.
        *args: Arguments to pass to the function.
        env: Optional environment variables dict (merged with os.environ).

    Returns:
        CompletedProcess with stdout, stderr, and returncode.
    """
    quoted_args = " ".join(f"'{a}'" for a in args)
    script = f'source "{lib_path}" && {function_name} {quoted_args}'
    run_env = {**os.environ, **(env or {})}
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=run_env,
    )


def run_bash_script(script: str, env: "dict | None" = None) -> subprocess.CompletedProcess:
    """Run an arbitrary bash script string.

    Args:
        script: Full bash script to execute.
        env: Optional environment variables dict (merged with os.environ).

    Returns:
        CompletedProcess with stdout, stderr, and returncode.
    """
    run_env = {**os.environ, **(env or {})}
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=run_env,
    )


@pytest.fixture
def bash_env(tmp_path):
    """Create a standard bash test environment with temp directories and env vars.

    Returns a dict with:
        - env: environment variables dict for subprocess calls
        - project_dir: path to the fake project directory
        - metrics_dir: path to the metrics directory
    """
    project_dir = tmp_path / "project"
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)

    env = {
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        "COGNITIVE_OS_SESSION_ID": "",
    }

    return {
        "env": env,
        "project_dir": project_dir,
        "metrics_dir": metrics_dir,
    }
