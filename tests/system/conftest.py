"""Shared fixtures for system-level infrastructure tests."""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def aos_dir(project_root: Path) -> Path:
    """Return the .cognitive-os directory path."""
    return project_root / ".cognitive-os"


@pytest.fixture(scope="session")
def hooks_dir(project_root: Path) -> Path:
    """Return the hooks directory path."""
    return project_root / "hooks"


@pytest.fixture(scope="session")
def config_path(aos_dir: Path) -> Path:
    """Return the cognitive-os.yaml config path."""
    return aos_dir / "cognitive-os.yaml"


@pytest.fixture(scope="session")
def compose_file(project_root: Path) -> Path:
    """Return the docker-compose file path."""
    return project_root / "docker-compose.cognitive-os.yml"


@pytest.fixture(scope="session")
def yaml_parser():
    """Return a function that validates YAML files.

    Tries yq first, falls back to python3 yaml module.
    """
    import yaml

    def _validate(filepath: Path) -> bool:
        try:
            with open(filepath) as f:
                yaml.safe_load(f)
            return True
        except Exception:
            return False

    return _validate


@pytest.fixture(scope="session")
def yaml_reader():
    """Return a function that reads a YAML field using dot notation."""
    import yaml

    def _read(filepath: Path, field: str):
        with open(filepath) as f:
            data = yaml.safe_load(f)
        keys = field.split(".")
        val = data
        for key in keys:
            if val is None or not isinstance(val, dict):
                return None
            val = val.get(key)
        return val

    return _read


@pytest.fixture
def run_hook(hooks_dir: Path, project_root: Path):
    """Return a helper to run a hook script with optional env overrides."""

    def _run(
        hook_name: str,
        env: Optional[dict] = None,
        stdin: Optional[str] = None,
        timeout: int = 30,
        cwd: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        hook_path = hooks_dir / hook_name
        run_env = os.environ.copy()
        run_env["CLAUDE_PROJECT_DIR"] = str(project_root)
        if env:
            run_env.update(env)
        return subprocess.run(
            ["bash", str(hook_path)],
            input=stdin,
            capture_output=True,
            text=True,
            env=run_env,
            timeout=timeout,
            cwd=cwd,
        )

    return _run
