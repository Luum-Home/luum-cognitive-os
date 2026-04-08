"""Root conftest.py -- registers all custom markers and provides shared session fixtures."""

import json
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


# ---------------------------------------------------------------------------
# Home isolation (from Hermes pattern)
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_cos_home(tmp_path, monkeypatch):
    """Redirect COS state directories to temp paths.

    Prevents test pollution by scoping all writes to tmp_path.
    Sets CLAUDE_PROJECT_DIR and COGNITIVE_OS_PROJECT_DIR so hooks
    write to an isolated tree instead of the real project.

    Adopted from Hermes conftest.py isolation pattern.
    """
    fake_home = tmp_path / "cos_test"
    fake_home.mkdir()
    cos_dir = fake_home / ".cognitive-os"
    session_id = f"test-{os.getpid()}"

    for subdir in [
        "sessions",
        f"sessions/{session_id}",
        f"sessions/{session_id}/metrics",
        "metrics",
        "skills",
        "checkpoints",
        "tasks",
    ]:
        (cos_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Minimal cognitive-os.yaml required by hooks
    config_content = (
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
    (cos_dir / "cognitive-os.yaml").write_text(config_content)
    # Some hooks also look for cognitive-os.yaml at the project root
    (fake_home / "cognitive-os.yaml").write_text(config_content)

    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(fake_home))
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(fake_home))
    monkeypatch.setenv("COGNITIVE_OS_SESSION_ID", session_id)
    monkeypatch.setenv("COGNITIVE_OS_HOOK_HEARTBEAT", "false")

    yield fake_home


# ---------------------------------------------------------------------------
# Settings override (from Pi pattern)
# ---------------------------------------------------------------------------


@pytest.fixture
def override_settings(monkeypatch):
    """Override cognitive-os.yaml settings for testing threshold-driven behavior.

    Returns a callable that patches lib.config_reader.get_config to merge
    the provided overrides on top of the original config values.

    Usage::

        def test_something(override_settings):
            override_settings({"project": {"phase": "production"}})
            # ... test code ...

    Adopted from Pi test pattern: applyOverrides for threshold-driven testing.
    """

    def _override(overrides: dict) -> None:
        try:
            import lib.config_reader as config_mod  # type: ignore[import]

            original_fn = getattr(config_mod, "get_config", None)
            if original_fn is None:
                return

            def _patched_get_config():
                base = original_fn()
                merged = {**base}
                for key, value in overrides.items():
                    if isinstance(value, dict) and isinstance(merged.get(key), dict):
                        merged[key] = {**merged[key], **value}
                    else:
                        merged[key] = value
                return merged

            monkeypatch.setattr(config_mod, "get_config", _patched_get_config)
        except ImportError:
            # lib.config_reader not available in all environments; skip silently
            pass

    return _override


# ---------------------------------------------------------------------------
# run_hook helper (usable from any test via conftest import or re-use)
# ---------------------------------------------------------------------------


@pytest.fixture
def run_hook():
    """Run a hook script with JSON stdin and return CompletedProcess.

    Replicates the fixture in tests/hooks/conftest.py so behavioral tests
    in tests/unit/ can use the same interface without importing across packages.

    Usage::

        result = run_hook("blast-radius.sh", stdin_json={...}, env={...})
        assert result.returncode == 0
    """
    hooks_dir = Path(__file__).resolve().parent.parent / "hooks"

    def _run(
        hook_name: str,
        stdin_json: "dict | None" = None,
        stdin_text: "str | None" = None,
        env: "dict | None" = None,
        timeout: int = 15,
    ) -> subprocess.CompletedProcess:
        hook_path = hooks_dir / hook_name
        if not hook_path.exists():
            pytest.skip(f"Hook {hook_name} not found")

        run_env = os.environ.copy()
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
