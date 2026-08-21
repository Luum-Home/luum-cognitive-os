"""Root conftest.py -- registers all custom markers and provides shared session fixtures.

Also installs a default `subprocess.run` timeout at module load time so test
suites that invoke external scripts cannot hang the whole suite when the
subprocess is buggy. Explicit `timeout=` values are honored only up to
the test-suite safety budget so subprocess cleanup fires before pytest-timeout.

Root-fix per 2026-05-12 session: the contracts/audit suites had ~169 naked
`subprocess.run(...)` calls without `timeout=`; one hang (test_repository_
family_ledgers_cover_hooks_skills_and_rules, test_cos_primitive_surface_
coverage_alias_json_exit_code_contract) blocked the entire suite at ~8%
completion. Pytest's `--timeout-method=thread` cannot kill an OS subprocess
spawned without `subprocess.run(timeout=...)`. This wrapper makes the
default safe; explicit per-call timeouts are capped by the safety budget.
"""

import os
import shutil
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Optional

import pytest
import yaml

# Make both the repository root and the tests package root importable in the
# parent process. Python's multiprocessing "spawn" start method copies this
# sys.path into child interpreters before unpickling Process targets. Pytest
# can collect tests/unit/*.py with module names like "unit.test_event_bus"
# because tests/unit has __init__.py; without tests/ itself on sys.path, child
# processes fail before running any worker code with:
#   ModuleNotFoundError: No module named 'unit'
_TESTS_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_ROOT.parent
_EXTRA_ROOTS = []

# MUTATION TESTING: la copia trae `cos_lib` y `tests`, pero NO `scripts`.
#
# `mutmut` copia a `<repo>/mutants/` solo lo que necesita mutar mas los tests.
# Cualquier test que haga `from scripts import ...` revienta ahi con
# ModuleNotFoundError, y la corrida entera muere en la fase de stats -- que
# colecta la suite completa, no el `test_command` configurado.
#
# El fuente real esta un nivel arriba y es el mismo arbol. Se lo agrega al final
# de sys.path, nunca al principio: lo que se esta mutando tiene que ganar. Si el
# origen se colara primero, mutmut mediria el codigo SIN mutar y todos los
# mutantes sobrevivirian -- un resultado catastrofico que se lee como "los tests
# no sirven" cuando lo que fallo es la ruta de importacion.
if _REPO_ROOT.name == "mutants" and (_REPO_ROOT.parent / ".git").exists():
    _EXTRA_ROOTS.append(str(_REPO_ROOT.parent))

for _path in (str(_REPO_ROOT), str(_TESTS_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)
for _path in _EXTRA_ROOTS:
    if _path not in sys.path:
        sys.path.append(_path)

# ----------------------------------------------------------------------------
# Default subprocess.run timeout (test-only safety net).
# ----------------------------------------------------------------------------
# Override via COS_TEST_SUBPROCESS_DEFAULT_TIMEOUT (seconds). Set to 0 to
# disable the wrapper entirely (legacy behavior). This value is also the max
# per-call subprocess timeout cap for tests that do not declare a tighter bound.
_DEFAULT_TEST_SUBPROCESS_TIMEOUT = float(
    os.environ.get("COS_TEST_SUBPROCESS_DEFAULT_TIMEOUT", "120")
)
# Budget of the pytest-timeout watchdog that will fire on the CURRENT test.
# Set per item in pytest_runtest_setup; falls back to the suite-level value.
_PYTEST_TIMEOUT_BUDGET_SECONDS: Optional[float] = None
_SUITE_TIMEOUT_BUDGET_SECONDS: Optional[float] = None

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

    def _effective_subprocess_timeout(requested: Any) -> Any:
        """Return a subprocess timeout that fires before pytest-timeout.

        Explicit call-site timeouts still express intent, but they cannot be
        allowed to exceed the suite-level watchdog. Otherwise pytest-timeout's
        thread dump wins first and the OS process tree remains alive.
        """
        if requested is None:
            requested = _DEFAULT_TEST_SUBPROCESS_TIMEOUT
        if _DEFAULT_TEST_SUBPROCESS_TIMEOUT > 0:
            requested = min(float(requested), _DEFAULT_TEST_SUBPROCESS_TIMEOUT)
        if _PYTEST_TIMEOUT_BUDGET_SECONDS and _PYTEST_TIMEOUT_BUDGET_SECONDS > 5:
            requested = min(float(requested), _PYTEST_TIMEOUT_BUDGET_SECONDS - 5)
        return requested

    def _subprocess_run_with_default_timeout(*args, **kwargs):
        """Inject/cap timeout; Popen.kill() handles whole-tree cleanup."""
        kwargs["timeout"] = _effective_subprocess_timeout(kwargs.get("timeout"))
        return _ORIG_SUBPROCESS_RUN(*args, **kwargs)

    # Patch at import time so test modules that import subprocess later still
    # see the wrapped version (subprocess is a module — late lookup). Patching
    # Popen globally is intentional: it protects direct Popen users as well as
    # subprocess.run's internal Popen construction.
    subprocess.Popen = _ProcessGroupPopen  # type: ignore[assignment,misc]
    subprocess.run = _subprocess_run_with_default_timeout  # type: ignore[assignment]


def _prefix_under_allowed_test_root(prefix: str, repo_root: Path) -> bool:
    """Return true when a venv prefix is valid for this checkout.

    Validation capsules intentionally symlink the source checkout's .venv into a
    detached worktree to avoid reinstalling dependencies for every broad test
    run. In that mode the tests are collected from the capsule, but sys.prefix
    resolves under COS_VALIDATION_SOURCE_PROJECT_DIR. That is still a governed
    repo venv and must not be mistaken for an arbitrary global interpreter.
    """
    roots = [repo_root.resolve()]
    source_root = os.environ.get("COS_VALIDATION_SOURCE_PROJECT_DIR", "").strip()
    if source_root:
        roots.append(Path(source_root).resolve())

    # MUTATION TESTING: la copia vive DENTRO del repo y usa su .venv.
    #
    # `mutmut` copia el fuente a `<repo>/mutants/` y corre pytest desde ahi. En esa
    # corrida `repo_root` --derivado de __file__-- es `<repo>/mutants`, pero
    # sys.prefix sigue siendo `<repo>/.venv`: un nivel ARRIBA. El chequeo fallaba y
    # rechazaba la corrida.
    #
    # Eso no era un detalle: es la razon real por la que `mutmut` estaba comprado,
    # declarado en pyproject con su bloque de configuracion, y con CERO invocaciones
    # desde que se instalo. El SO bloqueaba a la herramienta de la comunidad que
    # resolvia lo que el SO reimplementaba a mano -- 183 lineas de mutacion propia
    # para UN solo hook.
    #
    # Es la misma forma que la capsula de validacion de dos lineas mas arriba: un
    # arbol derivado que reusa el venv gobernado del origen. Se acepta subiendo por
    # los ancestros, y solo si el ancestro es un checkout de git. Un interprete
    # global --/usr, /opt/homebrew-- nunca cae bajo un ancestro con `.git`, asi que
    # la defensa que este guard existe para dar queda intacta.
    for ancestro in list(repo_root.resolve().parents)[:3]:
        if (ancestro / ".git").exists():
            roots.append(ancestro)
            break

    resolved_prefix = Path(prefix).resolve()
    for root in roots:
        try:
            resolved_prefix.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _enforce_runtime_invariants() -> None:
    """ADR-305: refuse to run tests in a runtime that diverges from pyproject's.

    The bus-benchmark Python 3.9 vs 3.14 footgun (2026-05-13) showed tests can
    "pass" simply by skipping/failing for environment reasons that nobody
    audits. This guard fails LOUD and EARLY instead.

    Two invariants, both relative to this file (no hardcoded user paths):

      1. Python minimum version matches pyproject.toml's `requires-python`.
      2. The interpreter is running from a venv rooted under the repo
         (sys.prefix points inside _REPO_ROOT and differs from sys.base_prefix).

    Bypass: PYTEST_ALLOW_NONVENV=1 (logged, emergency only). Operators who
    deliberately want to test on a different Python should override the
    minimum via PYTEST_REQUIRED_PYTHON_MAJOR_MINOR=3.X.
    """
    import sys
    import os
    from pathlib import Path

    # ── 1. Python version invariant ─────────────────────────────────────────
    required = os.environ.get("PYTEST_REQUIRED_PYTHON_MAJOR_MINOR", "3.11")
    try:
        req_major, req_minor = (int(x) for x in required.split("."))
    except ValueError:
        req_major, req_minor = 3, 11
    if sys.version_info < (req_major, req_minor):
        pytest.exit(
            f"COS test suite requires Python >= {req_major}.{req_minor}; "
            f"got {sys.version_info.major}.{sys.version_info.minor} at "
            f"{sys.executable}. Run via `.venv/bin/python -m pytest` or "
            f"`uv run pytest`. Override floor with "
            f"PYTEST_REQUIRED_PYTHON_MAJOR_MINOR=3.X (e.g. 3.14).",
            returncode=2,
        )

    # ── 2. Venv-under-repo invariant ────────────────────────────────────────
    if os.environ.get("PYTEST_ALLOW_NONVENV", "").strip() in ("1", "true", "yes"):
        return  # explicit bypass, no further check

    repo_root = Path(__file__).resolve().parent.parent
    in_venv = sys.prefix != sys.base_prefix
    prefix_under_repo = _prefix_under_allowed_test_root(sys.prefix, repo_root)

    if not (in_venv and prefix_under_repo):
        pytest.exit(
            f"COS tests must run from a venv rooted under the repo "
            f"({repo_root}). Got interpreter at {sys.executable} with "
            f"sys.prefix={sys.prefix}. Use `.venv/bin/python -m pytest` "
            f"or `uv run pytest`. Bypass with PYTEST_ALLOW_NONVENV=1 "
            f"(emergency only).",
            returncode=2,
        )


def _resolve_suite_timeout_budget(config) -> Optional[float]:
    """Seconds pytest-timeout will allow a test before it fires.

    Read the CLI flag FIRST and `pytest.ini` second, because they live in
    different places and only the flag was being read before.
    `config.getoption("timeout")` is the `--timeout=` value and defaults to
    None; `timeout = 30` in pytest.ini lands in `config.getini("timeout")`.
    A normal run passes no flag, so the budget stayed None and
    `_effective_subprocess_timeout` skipped its ordering clause entirely --
    measured 2026-08-20: DEFAULT=120.0 BUDGET=None EFFECTIVE(120)=120.0.

    The consequence was not cosmetic. With the budget unset, a subprocess got
    120 s while the watchdog fired at 30 s, and pytest.ini's
    `timeout_method = thread` cannot kill a subprocess: it dumps stacks and
    calls os._exit(1), taking the whole session down. Ordering the two
    budgets is what turns "the run aborted" into "this test is too slow".
    """
    for source in ("option", "ini"):
        try:
            raw = (
                config.getoption("timeout", default=None)
                if source == "option"
                else config.getini("timeout")
            )
        except (ValueError, KeyError):
            continue
        if not raw:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def _item_timeout_budget(item) -> Optional[float]:
    """The watchdog budget for ONE test: its own marker wins over the ini.

    Applying the suite value to every item would be wrong in both directions.
    56 tests carry `@pytest.mark.timeout(...)`, from 10 s to 1800 s; capping a
    30-minute test's subprocesses at 25 s, or letting a 10-second test spawn a
    115-second one, are the same bug with opposite signs.
    """
    marker = item.get_closest_marker("timeout")
    if marker is not None:
        raw = marker.kwargs.get("timeout")
        if raw is None and marker.args:
            raw = marker.args[0]
        try:
            value = float(raw)
        except (TypeError, ValueError):
            value = None
        if value:
            return value
    return _SUITE_TIMEOUT_BUDGET_SECONDS


def pytest_runtest_setup(item):
    """Point the subprocess cap at the watchdog that will actually fire."""
    global _PYTEST_TIMEOUT_BUDGET_SECONDS
    _PYTEST_TIMEOUT_BUDGET_SECONDS = _item_timeout_budget(item)


def pytest_runtest_teardown(item, nextitem):  # noqa: ARG001
    """Restore the suite budget so fixture/collection subprocesses are not
    left capped by whichever test happened to run last."""
    global _PYTEST_TIMEOUT_BUDGET_SECONDS
    _PYTEST_TIMEOUT_BUDGET_SECONDS = _SUITE_TIMEOUT_BUDGET_SECONDS


def pytest_configure(config):
    """Register all custom markers used across the test suite."""
    _enforce_runtime_invariants()
    global _PYTEST_TIMEOUT_BUDGET_SECONDS, _SUITE_TIMEOUT_BUDGET_SECONDS
    _SUITE_TIMEOUT_BUDGET_SECONDS = _resolve_suite_timeout_budget(config)
    _PYTEST_TIMEOUT_BUDGET_SECONDS = _SUITE_TIMEOUT_BUDGET_SECONDS

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
        "timeout(seconds): Per-test hard timeout override; also caps this test's subprocess budget (see _item_timeout_budget)",
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
    engram_bin = os.environ.get("ENGRAM_BIN", "").strip()
    if not engram_bin:
        local_bin = Path.home() / ".local" / "bin" / "engram"
        engram_bin = str(local_bin) if local_bin.exists() else (shutil.which("engram") or "")
    if not engram_bin or not Path(engram_bin).exists():
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
