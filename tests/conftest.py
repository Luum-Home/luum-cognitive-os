"""Root conftest.py -- registers all custom markers and provides shared session fixtures."""

import os
import shutil
import sqlite3
import subprocess
import uuid
from pathlib import Path
from typing import Any

import pytest
import yaml


def pytest_configure(config):
    """Register all custom markers used across the test suite."""
    markers = [
        "unit: Unit tests for individual library functions",
        "audit: Aspirational-component audit tests (gated from default CI)",
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
        "contract: Product contract tests that validate durable behavior",
        "timeout(seconds): Per-test hard timeout override used by pytest-timeout and conftest SIGALRM",
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
# Auto-marker injection — lane detection from test path (REQ-3, ADR-069)
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LANES_FILE = _PROJECT_ROOT / ".cognitive-os" / "test-lanes.yaml"


def _build_path_to_marker_map() -> dict[str, str]:
    """Load test-lanes.yaml and return a mapping from normalised path prefix to marker name.

    The marker name for a lane is the lane key, except ``hooks`` which maps to
    the ``hook`` marker (singular) to match the marker registered in pytest.ini.

    Cached at module level so the YAML file is read once per collection run.
    """
    if not _LANES_FILE.exists():
        return {}
    try:
        with _LANES_FILE.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        lanes: dict[str, Any] = data.get("lanes", {})
    except Exception:
        return {}

    mapping: dict[str, str] = {}
    for lane_name, config in lanes.items():
        # Lane name → marker name.  ``hooks`` lane uses ``hook`` marker (singular).
        marker_name = "hook" if lane_name == "hooks" else lane_name
        for path_prefix in config.get("paths", []):
            # Normalise: strip leading "./" and trailing "/" so startswith works cleanly.
            normalised = path_prefix.lstrip("./").rstrip("/")
            mapping[normalised] = marker_name
    return mapping


# Module-level cache — built once at import time so it is available before
# pytest_collection_modifyitems is called.
_PATH_TO_MARKER: dict[str, str] = _build_path_to_marker_map()


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:  # noqa: ANN401
    """Auto-inject lane markers based on each test's file path (REQ-3, ADR-069).

    Algorithm:
    1. Derive the path of each test item relative to the project root.
    2. Match it against the lane path prefixes from ``.cognitive-os/test-lanes.yaml``.
    3. If the item does not already carry that marker, add it.

    This is idempotent: running it twice does not duplicate markers because we
    check existing markers before adding.
    """
    if not _PATH_TO_MARKER:
        return  # YAML not available — degrade gracefully, no markers added

    for item in items:
        try:
            item_path = Path(item.fspath).resolve()
            rel = item_path.relative_to(_PROJECT_ROOT)
            rel_str = str(rel)
        except (ValueError, TypeError):
            continue

        for path_prefix, marker_name in _PATH_TO_MARKER.items():
            # Match on directory boundary: exact equality OR prefix followed by "/".
            # Prevents tests/unit_extra/ from matching the tests/unit lane.
            if rel_str == path_prefix or rel_str.startswith(path_prefix + "/"):
                existing_markers = {m.name for m in item.iter_markers()}
                if marker_name not in existing_markers:
                    item.add_marker(getattr(pytest.mark, marker_name))
                break  # first match wins — a test belongs to exactly one lane

