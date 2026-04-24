"""conftest.py for tests/e2e — defensive watchdog-leak detection.

Provides:
    * `repo_root` session-scoped fixture pointing at the real COS repo root
      (needed so test hooks can invoke the real scripts/lib).
    * `lingering_watchdog_guard` session-scoped, autouse fixture that records
      watchdog PIDs before the suite and warns/fails if any new daemon is still
      alive after the suite finishes (defensive against test leaks).

The guard uses `pgrep -f so_session_watchdog.py` — no psutil dependency.
"""

from __future__ import annotations

import os
import subprocess
import sys
import warnings
from pathlib import Path

import pytest


# ──────────────────────────────────────────────────────────────────────────
# Helpers (no external deps — safe in any CI)
# ──────────────────────────────────────────────────────────────────────────

def _watchdog_pids() -> set[int]:
    """Return the set of PIDs whose cmdline contains so_session_watchdog.py.

    Uses pgrep -f (POSIX on Linux/macOS). Returns empty set on failure.
    """
    try:
        result = subprocess.run(
            ["pgrep", "-f", "so_session_watchdog.py"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return set()
    if result.returncode not in (0, 1):  # 1 = no matches
        return set()
    pids: set[int] = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pids.add(int(line))
        except ValueError:
            continue
    return pids


def _kill_pid(pid: int) -> None:
    """Best-effort TERM then KILL."""
    import signal
    import time

    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(pid, sig)
        except (ProcessLookupError, PermissionError):
            return
        time.sleep(0.2)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return


# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Real repo root (for sourcing real hooks/scripts/lib during tests)."""
    here = Path(__file__).resolve()
    # tests/e2e/conftest.py → repo_root is two parents up.
    root = here.parent.parent.parent
    assert (root / ".claude" / "settings.json").is_file(), (
        f"Expected .claude/settings.json at {root}, refusing to run e2e tests "
        "against a non-COS repo."
    )
    return root


@pytest.fixture(scope="session", autouse=True)
def lingering_watchdog_guard(repo_root: Path):
    """Record watchdog PIDs before and after the suite. Warn on leaks.

    This fixture does NOT fail the run — it emits a warning AND attempts to
    clean up any leaked processes so the next test run starts clean. Tests
    themselves should clean up; this is defense-in-depth.
    """
    before = _watchdog_pids()
    yield
    after = _watchdog_pids()
    leaked = after - before
    if leaked:
        warnings.warn(
            f"tests/e2e leaked {len(leaked)} so_session_watchdog.py "
            f"process(es): {sorted(leaked)}. Auto-killing now.",
            stacklevel=1,
        )
        for pid in leaked:
            _kill_pid(pid)


@pytest.fixture(scope="session", autouse=True)
def _skip_unsupported_platform():
    """All e2e tests here are POSIX-only (bash + pgrep)."""
    if not (sys.platform.startswith("darwin") or sys.platform.startswith("linux")):
        pytest.skip("e2e startup smoke tests are macOS/Linux only")
