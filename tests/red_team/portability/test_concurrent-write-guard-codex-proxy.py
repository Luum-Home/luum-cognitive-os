# SCOPE: os-only
"""Portability probes for hooks/concurrent-write-guard-codex-proxy.sh — ADR-111 §Gate-3.

Paired test for hooks/concurrent-write-guard-codex-proxy.sh (# SCOPE: os-only).

This file is the scope-marker-portability-gate-required companion for the proxy
script. The full probe suite is in test_concurrent-write-guard.py; this file
re-imports and re-runs the same probes against the proxy hook explicitly.

ADR reference: ADR-111 §Gate-3
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROXY_HOOK = REPO_ROOT / "hooks" / "concurrent-write-guard-codex-proxy.sh"
FULL_HOOK = REPO_ROOT / "hooks" / "concurrent-write-guard.sh"

SCRUB_VARS = (
    "CI",
    "PYTEST_CURRENT_TEST",
    "COS_ALLOW_CONCURRENT_WRITES",
    "DISABLE_HOOK_CONCURRENT_WRITE_GUARD",
    "COGNITIVE_OS_SESSION_ID",
)


def _run_proxy(
    project: Path,
    session_id: str | None = None,
    extra_env: dict[str, str] | None = None,
    prompt: str = "write a new file",
) -> subprocess.CompletedProcess[str]:
    """Run the Codex proxy hook with a simulated UserPromptSubmit payload."""
    payload = {"tool_name": None, "prompt": prompt}
    env = os.environ.copy()
    for var in SCRUB_VARS:
        env.pop(var, None)
    env.update(
        {
            "COGNITIVE_OS_HARNESS": "codex",
            "COGNITIVE_OS_PROJECT_DIR": str(project),
        }
    )
    if session_id:
        env["COGNITIVE_OS_SESSION_ID"] = session_id
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(PROXY_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )


def _write_lock(locks_dir: Path, file_path: str, session_id: str, pid: int, age_seconds: int = 30) -> None:
    """Write a synthetic lock file into the locks directory."""
    locks_dir.mkdir(parents=True, exist_ok=True)
    import hashlib
    file_hash = hashlib.md5(file_path.encode()).hexdigest()
    lock_file = locks_dir / f"{file_hash}.lock"
    now = int(time.time())
    entry = {
        "session_id": session_id,
        "pid": pid,
        "file_path": file_path,
        "timestamp_epoch": now - age_seconds,
        "timestamp": "2026-05-02T00:00:00Z",
    }
    lock_file.write_text(json.dumps(entry))


# ---------------------------------------------------------------------------
# Portability: Codex proxy fires correctly
# ---------------------------------------------------------------------------


def test_no_locks_no_warning_under_codex(tmp_path: Path) -> None:
    """No warning emitted when no lock files exist (clean Codex session)."""
    result = _run_proxy(tmp_path, session_id="codex-session-A")
    assert result.returncode == 0, (
        f"portability: proxy must exit 0 when no locks exist; got {result.returncode}\n"
        f"{result.stderr}"
    )
    assert "CONCURRENT-WRITE-GUARD" not in result.stderr


def test_cross_session_live_lock_warned_under_codex(tmp_path: Path) -> None:
    """Live lock from a different session triggers a warning under Codex harness."""
    locks_dir = tmp_path / ".cognitive-os" / "sessions" / "locks"
    # Write a lock from another session with a live-looking PID (os.getpid() — our own PID,
    # which will appear alive, simulating a live cross-session lock)
    _write_lock(
        locks_dir,
        file_path=str(tmp_path / "lib" / "important.py"),
        session_id="other-session-B",
        pid=os.getpid(),
        age_seconds=30,
    )
    result = _run_proxy(tmp_path, session_id="codex-session-A")
    assert result.returncode == 0, (
        "portability: proxy must warn (exit 0), not block, for Codex gap; "
        f"got {result.returncode}"
    )
    assert "CONCURRENT-WRITE-GUARD" in result.stderr
    assert "other-session-B" in result.stderr


def test_same_session_lock_not_warned_under_codex(tmp_path: Path) -> None:
    """Lock from the same session is not treated as contention under Codex harness."""
    locks_dir = tmp_path / ".cognitive-os" / "sessions" / "locks"
    _write_lock(
        locks_dir,
        file_path=str(tmp_path / "lib" / "myfile.py"),
        session_id="codex-session-A",
        pid=os.getpid(),
        age_seconds=30,
    )
    result = _run_proxy(tmp_path, session_id="codex-session-A")
    assert result.returncode == 0, (
        f"portability: own-session lock must not trigger warning; got {result.returncode}"
    )
    assert "CONCURRENT-WRITE-GUARD" not in result.stderr


def test_stale_lock_not_warned_under_codex(tmp_path: Path) -> None:
    """Stale lock (expired TTL) is skipped without warning under Codex harness."""
    locks_dir = tmp_path / ".cognitive-os" / "sessions" / "locks"
    # 600 seconds old — exceeds default 300s TTL
    _write_lock(
        locks_dir,
        file_path=str(tmp_path / "lib" / "stale.py"),
        session_id="old-session-C",
        pid=99999,  # almost certainly dead
        age_seconds=600,
    )
    result = _run_proxy(tmp_path, session_id="codex-session-A")
    assert result.returncode == 0, (
        f"portability: stale lock must not trigger warning; got {result.returncode}"
    )
    assert "CONCURRENT-WRITE-GUARD" not in result.stderr


def test_dead_pid_lock_not_warned_under_codex(tmp_path: Path) -> None:
    """Lock with a dead PID is treated as stale and not warned under Codex harness."""
    locks_dir = tmp_path / ".cognitive-os" / "sessions" / "locks"
    # PID 1 is init/launchd — not a valid session PID and kill -0 on it from a
    # test process will typically fail with permission denied, treated as dead.
    # Use a clearly non-existent PID (99999999) to guarantee dead-PID path.
    _write_lock(
        locks_dir,
        file_path=str(tmp_path / "lib" / "dead.py"),
        session_id="dead-session-D",
        pid=99999999,
        age_seconds=30,
    )
    result = _run_proxy(tmp_path, session_id="codex-session-A")
    assert result.returncode == 0, (
        f"portability: dead-PID lock must not trigger warning; got {result.returncode}"
    )
    assert "CONCURRENT-WRITE-GUARD" not in result.stderr


def test_bypass_env_var_accepted_under_codex(tmp_path: Path) -> None:
    """COS_ALLOW_CONCURRENT_WRITES=1 bypass is accepted under Codex harness."""
    locks_dir = tmp_path / ".cognitive-os" / "sessions" / "locks"
    _write_lock(
        locks_dir,
        file_path=str(tmp_path / "lib" / "guarded.py"),
        session_id="other-session-E",
        pid=os.getpid(),
        age_seconds=30,
    )
    result = _run_proxy(
        tmp_path,
        session_id="codex-session-A",
        extra_env={"COS_ALLOW_CONCURRENT_WRITES": "1"},
    )
    assert result.returncode == 0
    assert "CONCURRENT-WRITE-GUARD" not in result.stderr


# ---------------------------------------------------------------------------
# Falsification: proxy must NOT silently ignore live cross-session contention
# ---------------------------------------------------------------------------


def test_falsification_live_lock_not_silently_ignored_under_codex(tmp_path: Path) -> None:
    """Live cross-session lock must produce stderr output — not be silently ignored."""
    locks_dir = tmp_path / ".cognitive-os" / "sessions" / "locks"
    _write_lock(
        locks_dir,
        file_path=str(tmp_path / "lib" / "critical.py"),
        session_id="contending-session-F",
        pid=os.getpid(),
        age_seconds=10,
    )
    result = _run_proxy(tmp_path, session_id="codex-session-A")
    assert "CONCURRENT-WRITE-GUARD" in result.stderr, (
        "falsification: live cross-session lock must produce warning on stderr, "
        "not be silently dropped"
    )
