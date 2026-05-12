"""Root conftest.py -- registers all custom markers and provides shared session fixtures.

Also installs a default `subprocess.run` timeout at module load time so test
suites that invoke external scripts cannot hang the whole suite when the
subprocess is buggy. Tests that need longer can still pass an explicit
`timeout=` keyword — that wins.

Root-fix per 2026-05-12 session: the contracts/audit suites had ~169 naked
`subprocess.run(...)` calls without `timeout=`; one hang (test_repository_
family_ledgers_cover_hooks_skills_and_rules, test_cos_primitive_surface_
coverage_alias_json_exit_code_contract) blocked the entire suite at ~8%
completion. Pytest's `--timeout-method=thread` cannot kill an OS subprocess
spawned without `subprocess.run(timeout=...)`. This wrapper makes the
default safe; explicit per-call timeouts still override.
"""

import os
import shutil
import sqlite3
import subprocess
import uuid
from pathlib import Path
from typing import Any

import pytest
import yaml

# ----------------------------------------------------------------------------
# Default subprocess.run timeout (test-only safety net).
# ----------------------------------------------------------------------------
# Override via COS_TEST_SUBPROCESS_DEFAULT_TIMEOUT (seconds). Set to 0 to
# disable the wrapper entirely (legacy behavior).
_DEFAULT_TEST_SUBPROCESS_TIMEOUT = float(
    os.environ.get("COS_TEST_SUBPROCESS_DEFAULT_TIMEOUT", "45")
)

if _DEFAULT_TEST_SUBPROCESS_TIMEOUT > 0:
    import signal

    _ORIG_SUBPROCESS_RUN = subprocess.run
    _ORIG_POPEN = subprocess.Popen

    class _ProcessGroupPopen(_ORIG_POPEN):  # type: ignore[misc,valid-type]
        """Popen that gives each spawned command its own killable process group.

        The important bit is not only `start_new_session=True`; it is also
        overriding `kill()`/`terminate()`. `subprocess.run(timeout=...)` calls
        `process.kill()` when the timeout fires. If `kill()` only signals the
        immediate child, grandchildren can survive and keep inherited stdout or
        stderr pipes open, causing the final `communicate()` drain to block in
        `select.poll()`. Killing the process group closes that whole tree.
        """

        def __init__(self, *args, **kwargs):
            self._cos_owns_process_group = False
            if os.name == "posix":
                caller_sets_session = kwargs.get("start_new_session") is True
                caller_sets_group = kwargs.get("process_group", None) is not None
                caller_sets_preexec = kwargs.get("preexec_fn", None) is not None
                if not caller_sets_session and not caller_sets_group and not caller_sets_preexec:
                    kwargs["start_new_session"] = True
                    self._cos_owns_process_group = True
                elif caller_sets_session or caller_sets_group:
                    self._cos_owns_process_group = True
            super().__init__(*args, **kwargs)

        def _signal_process_group(self, sig: int) -> None:
            if os.name != "posix" or not self._cos_owns_process_group:
                super().send_signal(sig)
                return
            try:
                os.killpg(os.getpgid(self.pid), sig)
            except ProcessLookupError:
                return
            except OSError:
                # Fall back to stdlib behavior if the process has already
                # exited, changed groups, or the platform rejects killpg.
                super().send_signal(sig)

        def send_signal(self, sig: int) -> None:
            self._signal_process_group(sig)

        def terminate(self) -> None:
            if os.name == "posix":
                self._signal_process_group(signal.SIGTERM)
            else:
                super().terminate()

        def kill(self) -> None:
            if os.name == "posix":
                self._signal_process_group(signal.SIGKILL)
            else:
                super().kill()

    def _subprocess_run_with_default_timeout(*args, **kwargs):
        """Inject default timeout; Popen.kill() handles whole-tree cleanup."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = _DEFAULT_TEST_SUBPROCESS_TIMEOUT
        return _ORIG_SUBPROCESS_RUN(*args, **kwargs)

    # Patch at import time so test modules that import subprocess later still
    # see the wrapped version (subprocess is a module — late lookup). Patching
    # Popen globally is intentional: it protects direct Popen users as well as
    # subprocess.run's internal Popen construction.
    subprocess.Popen = _ProcessGroupPopen  # type: ignore[assignment,misc]
    subprocess.run = _subprocess_run_with_default_timeout  # type: ignore[assignment]


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
            # A directory can have explicit sublanes (for example
            # integration-docker). The first declared lane owns automatic
            # path-based marking; sublanes must select via marker_include so
            # they do not overwrite the default directory marker.
            mapping.setdefault(normalised, marker_name)
    return mapping


# Module-level cache — built once at import time so it is available before
# pytest_collection_modifyitems is called.
_PATH_TO_MARKER: dict[str, str] = _build_path_to_marker_map()


# ---------------------------------------------------------------------------
# Quarantine registry — ADR-100 last-line-of-defense for known flakes
# ---------------------------------------------------------------------------

_QUARANTINE_FILE = Path(__file__).resolve().parent / "quarantine.yaml"


def _load_quarantine() -> dict[str, dict[str, Any]]:
    """Load tests/quarantine.yaml into a {nodeid: entry} mapping.

    Tests with a quarantine entry are auto-skipped at collection time. Each
    entry records the reason, when it was added, and the ticket that owns the
    fix. Empty/missing file → empty registry (no skips).
    """
    if not _QUARANTINE_FILE.exists():
        return {}
    try:
        with _QUARANTINE_FILE.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        entries = data.get("quarantine") or []
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        nodeid = entry.get("nodeid")
        if not nodeid:
            continue
        out[nodeid] = entry
    return out


_QUARANTINE: dict[str, dict[str, Any]] = _load_quarantine()


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:  # noqa: ANN401
    """Auto-inject lane markers + apply quarantine skips.

    Two passes over the collected items:

    1. Lane marker injection (REQ-3, ADR-072): match item path against lane
       prefixes from ``.cognitive-os/test-lanes.yaml`` and add the lane's
       marker if not already present. Boundary-safe (tests/unit_extra/ does
       NOT match the unit lane).

    2. Quarantine skip (ADR-100): if the item's nodeid is listed in
       ``tests/quarantine.yaml``, add ``pytest.mark.skip`` with a
       ``[QUARANTINE]`` reason that includes the ticket. Quarantine is
       the LAST line of defense — root-fix when possible, retry via
       pytest-rerunfailures when transient, quarantine only when both fail.

    Both passes are idempotent.
    """
    # Pass 1: lane markers
    if _PATH_TO_MARKER:
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

    # Pass 2: quarantine skips
    if _QUARANTINE:
        for item in items:
            entry = _QUARANTINE.get(item.nodeid)
            if entry is None:
                continue
            reason = entry.get("reason", "no reason given")
            ticket = entry.get("ticket", "no ticket")
            since = entry.get("since", "?")
            item.add_marker(
                pytest.mark.skip(
                    reason=f"[QUARANTINE since {since} | {ticket}] {reason}"
                )
            )
