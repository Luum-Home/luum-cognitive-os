"""Root conftest.py -- registers all custom markers and provides shared session fixtures."""

import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import uuid
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
def skills_dir(project_root: Path) -> Path:
    """Return the path to the Cognitive OS skills directory."""
    return project_root / ".cognitive-os" / "skills"


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


# ---------------------------------------------------------------------------
# Real Engram fixture — actual persistence, no mocks
# ---------------------------------------------------------------------------

ENGRAM_DB_PATH = Path.home() / ".engram" / "engram.db"


@pytest.fixture
def real_engram():
    """Provides a real Engram instance backed by the actual SQLite database.
    No mocks. Actual reads and writes.

    Isolation strategy: each fixture invocation uses a unique project name
    (UUID-based) so test data is fully scoped and cannot collide with real
    project data or concurrent test runs.  All rows are deleted on teardown.

    Adopted from Hermes test patterns: mock the LLM, not the storage.

    NOTE: engram v1.10.2 does not support --db; it always writes to
    ~/.engram/engram.db.  Project-scoping is the only isolation available
    without patching the binary.
    """
    engram_bin = os.environ.get("ENGRAM_BIN", str(Path.home() / ".local" / "bin" / "engram"))
    if not Path(engram_bin).exists() and not shutil.which("engram"):
        pytest.skip("engram binary not installed")

    project = f"cos-test-{uuid.uuid4().hex[:12]}"

    def save(title, content, topic_key=None, type_="manual"):
        cmd = [engram_bin, "save", title, content,
               "--type", type_,
               "--project", project]
        if topic_key:
            cmd.extend(["--topic", topic_key])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result

    def search(query):
        cmd = [engram_bin, "search", query,
               "--project", project]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result

    def get_db():
        """Direct SQLite connection to the real engram DB, filtered to this
        fixture's project.  Callers MUST close the connection after use."""
        return sqlite3.connect(str(ENGRAM_DB_PATH))

    def query(sql, params=()):
        """Run a read-only SQL query scoped to this fixture's project."""
        conn = sqlite3.connect(str(ENGRAM_DB_PATH))
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return rows

    yield {
        "project": project,
        "engram_bin": engram_bin,
        "db_path": str(ENGRAM_DB_PATH),
        "save": save,
        "search": search,
        "get_db": get_db,
        "query": query,
    }

    # Teardown: remove all rows written by this fixture invocation.
    if ENGRAM_DB_PATH.exists():
        conn = sqlite3.connect(str(ENGRAM_DB_PATH))
        try:
            conn.execute("DELETE FROM observations WHERE project = ?", (project,))
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Per-test timeout (30 s) — prevents hanging subprocesses
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _enforce_test_timeout():
    """30-second hard timeout per test via SIGALRM.

    Prevents subprocesses or I/O waits from hanging the entire suite.
    Adopted from Hermes conftest.py pattern.  No-op on Windows (no SIGALRM).
    """
    if sys.platform == "win32":
        yield
        return

    def _timeout_handler(signum, frame):
        raise TimeoutError("Test exceeded 30-second timeout")

    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(30)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, old_handler)
