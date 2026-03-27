"""Root conftest.py -- registers all custom markers and provides shared session fixtures."""

import shutil
import subprocess
from pathlib import Path

import pytest


def pytest_configure(config):
    """Register all custom markers used across the test suite."""
    markers = [
        "unit: Unit tests for individual library functions",
        "behavior: Behavior tests validating hook and skill interactions",
        "integration: Integration tests spanning multiple components",
        "system: System-level infrastructure tests (config, docker, metrics, rules)",
        "docker: Requires Docker daemon to be running",
        "slow: Slow tests (deselect with '-m \"not slow\"')",
        "e2e: End-to-end tests spanning multiple services",
        "eval_frameworks: Evaluation framework tests (deepeval, ragas, promptfoo)",
        "arena: Competitive arena benchmark tests",
        "benchmark: Performance benchmark tests",
        "quality: LLM-evaluated quality tests",
    ]
    for marker in markers:
        config.addinivalue_line("markers", marker)


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def docker_available():
    """Check whether Docker is installed and the daemon is running.

    Skips the test automatically if Docker is not usable.
    """
    if not shutil.which("docker"):
        pytest.skip("Docker not installed")
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pytest.skip("Docker daemon not running")
    return True
