"""ADR-028 Phase B D2 contract: file-descriptor invariants.

Asserts that representative hook scripts do not leak file descriptors.
Runs each probed hook under a controlled environment, captures the FD
count of the calling Python process before and after, and fails if the
delta exceeds a narrow tolerance.

Platform: macOS + Linux. On macOS we use `lsof -p`; on Linux we use
`/proc/self/fd`. Skipped on other platforms.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


_ROOT = Path(__file__).resolve().parent.parent.parent


def _count_open_fds_self() -> int:
    """Return the number of open file descriptors for this process."""
    # Prefer /proc (Linux, fast).
    proc_fd = Path("/proc/self/fd")
    if proc_fd.is_dir():
        return sum(1 for _ in proc_fd.iterdir())
    # macOS fallback via lsof.
    if sys.platform == "darwin":
        try:
            r = subprocess.run(
                ["lsof", "-p", str(os.getpid())],
                capture_output=True, text=True, timeout=10,
            )
            # First line is header; count the rest.
            return max(0, len(r.stdout.splitlines()) - 1)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("lsof unavailable on macOS; cannot measure FD count")
    pytest.skip(f"FD counting not supported on {sys.platform}")


def _run_hook(script_path: Path, stdin_data: str = "") -> subprocess.CompletedProcess:
    """Run a shell hook in a subprocess with a 30s timeout."""
    env = os.environ.copy()
    env.setdefault("CLAUDE_PROJECT_DIR", str(_ROOT))
    return subprocess.run(
        ["bash", str(script_path)],
        input=stdin_data,
        capture_output=True, text=True, timeout=30,
        env=env, cwd=str(_ROOT),
    )


# ---------------------------------------------------------------------------


def test_metrics_rotation_does_not_leak_fds():
    """Running hooks/metrics-rotation.sh must not leave extra FDs open in us.

    The hook itself runs in a subprocess, so any FDs IT opens are cleaned
    up when the subprocess exits. What we're asserting is that the act of
    spawning it and reading its output doesn't leak on our side.
    """
    script = _ROOT / "hooks" / "metrics-rotation.sh"
    if not script.is_file():
        pytest.skip("metrics-rotation.sh not present")

    before = _count_open_fds_self()
    for _ in range(3):
        r = _run_hook(script)
        assert r.returncode == 0, f"hook exited {r.returncode}: {r.stderr[:200]}"
    after = _count_open_fds_self()

    delta = after - before
    # A small delta can come from logging handlers or pytest's own capture;
    # > 5 after 3 invocations is a real leak.
    assert delta <= 5, f"FD leak detected: before={before} after={after} delta={delta}"


def test_so_vitals_script_does_not_leak_fds():
    script = _ROOT / "scripts" / "so-vitals.sh"
    if not script.is_file():
        pytest.skip("so-vitals.sh not present")

    before = _count_open_fds_self()
    for _ in range(3):
        r = _run_hook(script)
        assert r.returncode == 0, f"so-vitals exited {r.returncode}: {r.stderr[:200]}"
    after = _count_open_fds_self()

    delta = after - before
    assert delta <= 5, f"FD leak detected: before={before} after={after} delta={delta}"


def test_reinvention_check_does_not_leak_fds_on_empty_stdin():
    """reinvention-check.sh should no-op silently on empty stdin."""
    script = _ROOT / "hooks" / "reinvention-check.sh"
    if not script.is_file():
        pytest.skip("reinvention-check.sh not present")

    before = _count_open_fds_self()
    for _ in range(3):
        r = _run_hook(script, stdin_data="")
        # exit 0 expected (advisory hook, no stdin = nothing to check)
        assert r.returncode == 0, f"hook exited {r.returncode}: {r.stderr[:200]}"
    after = _count_open_fds_self()

    delta = after - before
    assert delta <= 5, f"FD leak detected: before={before} after={after} delta={delta}"


def test_fd_count_is_measurable():
    """Sanity: the counter returns a positive number on this platform."""
    n = _count_open_fds_self()
    assert isinstance(n, int) and n > 0, f"expected positive FD count, got {n!r}"
