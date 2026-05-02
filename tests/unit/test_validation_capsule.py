"""Tests for validation capsule isolation and concurrent-agent suppression."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parents[1].parent
CAPSULE = PROJECT_ROOT / "scripts" / "cos-validation-capsule.sh"
PRE_AGENT_SNAPSHOT = PROJECT_ROOT / "hooks" / "pre-agent-snapshot.sh"
PROFILE_AUTOAPPLY = PROJECT_ROOT / "hooks" / "profile-drift-autoapply.sh"


def test_validation_capsule_runs_in_isolated_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("unit repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, capture_output=True)

    result = subprocess.run(
        [
            "bash",
            str(CAPSULE),
            "--allow-dirty",
            "--name",
            "unit-guards",
            "--",
            "bash",
            "-c",
            "pwd; test -z \"${COGNITIVE_OS_PROJECT_DIR:-}\" && test -n \"${COS_VALIDATION_SOURCE_PROJECT_DIR:-}\"",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    capsule_pwd = result.stdout.strip().splitlines()[0]
    assert str(repo) not in capsule_pwd
    assert "cos-validation-capsules" in capsule_pwd
    assert not (repo / ".cognitive-os" / "runtime" / "validation-capsule.lock").exists()

def test_validation_lock_helper_treats_live_lock_as_active(tmp_path: Path) -> None:
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "validation-capsule.lock").write_text(
        json.dumps(
            {
                "run_id": "unit",
                "pid": os.getpid(),
                "expires_at_epoch": int(time.time()) + 120,
                "message": "unit validation",
            }
        )
        + "\n"
    )
    result = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{PROJECT_ROOT}/hooks/_lib/validation-lock.sh"; cos_validation_lock_active "{tmp_path}"',
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_dispatch_gate_blocks_agent_launch_during_validation_capsule(tmp_path: Path) -> None:
    runtime = tmp_path / ".cognitive-os" / "runtime"
    metrics = tmp_path / ".cognitive-os" / "metrics"
    runtime.mkdir(parents=True)
    metrics.mkdir(parents=True)
    (runtime / "validation-capsule.lock").write_text(
        json.dumps(
            {
                "run_id": "unit",
                "pid": os.getpid(),
                "expires_at_epoch": int(time.time()) + 120,
                "message": "unit validation lock",
            }
        )
        + "\n"
    )
    payload = {"tool_name": "Agent", "tool_input": {"prompt": "change files"}}
    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "hooks" / "dispatch-gate.sh")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "COS_VALIDATION_ALLOW_CONCURRENT_AGENTS": "0",
        },
        timeout=5,
    )
    assert result.returncode == 2
    assert "validation capsule active" in result.stderr


def test_pre_agent_snapshot_suppression_does_not_stash_dirty_work(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    tracked = repo / "tracked.txt"
    tracked.write_text("base\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, capture_output=True)
    tracked.write_text("dirty\n")

    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(repo),
        "COS_SUPPRESS_AGENT_SNAPSHOT": "1",
        "COGNITIVE_OS_SESSION_ID": "unit-validation",
    }
    result = subprocess.run(
        ["bash", str(PRE_AGENT_SNAPSHOT)],
        cwd=repo,
        env=env,
        input='{"tool_name":"Agent","tool_input":{"description":"unit"}}',
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert tracked.read_text() == "dirty\n"
    stash = subprocess.run(["git", "stash", "list"], cwd=repo, text=True, capture_output=True, check=True)
    assert "auto-pre-agent" not in stash.stdout


def test_profile_autoapply_respects_validation_mode() -> None:
    content = PROFILE_AUTOAPPLY.read_text()
    assert "cos_validation_lock_active" in content
    assert "COS_DISABLE_PROFILE_AUTOAPPLY" in content


# ---------------------------------------------------------------------------
# ADR-113 liveness primitive tests
# ---------------------------------------------------------------------------

VALIDATION_LOCK = PROJECT_ROOT / "hooks" / "_lib" / "validation-lock.sh"
CLEANUP_HOOK = PROJECT_ROOT / "hooks" / "validation-lock-cleanup.sh"


def _write_lock(runtime: Path, data: dict) -> Path:
    """Write a validation-capsule.lock and return its path."""
    lock_path = runtime / "validation-capsule.lock"
    lock_path.write_text(json.dumps(data) + "\n", encoding="utf-8")
    return lock_path


def _call_lock_active(project_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "bash",
            "-c",
            f'source "{VALIDATION_LOCK}"; cos_validation_lock_active "{project_dir}"',
        ],
        capture_output=True,
        text=True,
    )


# ── P1 heartbeat staleness ────────────────────────────────────────────────────

def test_heartbeat_staleness_removes_lock_and_returns_stale(tmp_path: Path) -> None:
    """P1: cos_validation_lock_active returns 1 (stale) and removes the lock
    when last_heartbeat_epoch is older than 3 × heartbeat_interval_seconds.
    """
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)

    interval = 30
    # Place heartbeat 4 × interval in the past — clearly past the 3× threshold.
    stale_heartbeat = int(time.time()) - (4 * interval)

    _write_lock(
        runtime,
        {
            "run_id": "unit-hb-stale",
            "pid": os.getpid(),
            "expires_at_epoch": int(time.time()) + 600,
            "started_at_epoch": int(time.time()) - 300,
            "last_heartbeat_epoch": stale_heartbeat,
            "heartbeat_interval_seconds": interval,
            "capsule_dir": str(tmp_path / "capsule"),
            "message": "heartbeat staleness test",
        },
    )

    result = _call_lock_active(tmp_path)

    assert result.returncode == 1, (
        f"Expected stale (rc=1) but got {result.returncode}. stderr={result.stderr}"
    )
    lock_path = runtime / "validation-capsule.lock"
    assert not lock_path.exists(), "Stale lock must be removed by cos_validation_lock_active"


def test_heartbeat_fresh_within_threshold_is_not_stale(tmp_path: Path) -> None:
    """P1 negative: fresh heartbeat (<3× interval old) must not be classified stale."""
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)

    interval = 30
    recent_heartbeat = int(time.time()) - (2 * interval)  # 2× — still within 3×

    _write_lock(
        runtime,
        {
            "run_id": "unit-hb-fresh",
            "pid": os.getpid(),
            "expires_at_epoch": int(time.time()) + 600,
            "started_at_epoch": int(time.time()) - 60,
            "last_heartbeat_epoch": recent_heartbeat,
            "heartbeat_interval_seconds": interval,
            "capsule_dir": str(tmp_path / "capsule"),
            "message": "fresh heartbeat test",
        },
    )

    result = _call_lock_active(tmp_path)

    # Live PID + fresh heartbeat → active (rc=0)
    assert result.returncode == 0, (
        f"Expected active (rc=0) for fresh heartbeat but got {result.returncode}"
    )


# ── P2 activity staleness ─────────────────────────────────────────────────────

def test_activity_staleness_detected_via_threshold_env(tmp_path: Path) -> None:
    """P2: activity log with old timestamp marks lock stale when
    COS_VALIDATION_ACTIVITY_THRESHOLD is set to a small value.
    """
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)

    # Write a lock with live PID and fresh heartbeat so only activity triggers stale.
    interval = 30
    _write_lock(
        runtime,
        {
            "run_id": "unit-activity-stale",
            "pid": os.getpid(),
            "expires_at_epoch": int(time.time()) + 600,
            "started_at_epoch": int(time.time()) - 300,
            "last_heartbeat_epoch": int(time.time()) - 5,  # fresh heartbeat
            "heartbeat_interval_seconds": interval,
            "capsule_dir": str(tmp_path / "capsule"),
            "message": "activity staleness test",
        },
    )

    # Write activity log with a timestamp 120s in the past.
    old_ts = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 120)
    )
    activity_log = runtime / "validation-activity.jsonl"
    activity_log.write_text(
        json.dumps({"ts": old_ts, "capsule": "unit-activity-stale", "action": "test_run"}) + "\n",
        encoding="utf-8",
    )

    env = {
        **os.environ,
        "COS_VALIDATION_ACTIVITY_THRESHOLD": "60",  # 60s threshold → 120s old → stale
    }

    result = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{VALIDATION_LOCK}"; cos_validation_lock_active "{tmp_path}"',
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1, (
        f"Expected activity-stale (rc=1) but got {result.returncode}. stderr={result.stderr}"
    )


def test_activity_log_within_threshold_is_not_stale(tmp_path: Path) -> None:
    """P2 negative: fresh activity log entry must not trigger stale detection."""
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)

    interval = 30
    _write_lock(
        runtime,
        {
            "run_id": "unit-activity-fresh",
            "pid": os.getpid(),
            "expires_at_epoch": int(time.time()) + 600,
            "started_at_epoch": int(time.time()) - 120,
            "last_heartbeat_epoch": int(time.time()) - 5,
            "heartbeat_interval_seconds": interval,
            "capsule_dir": str(tmp_path / "capsule"),
            "message": "activity fresh test",
        },
    )

    recent_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 10))
    activity_log = runtime / "validation-activity.jsonl"
    activity_log.write_text(
        json.dumps({"ts": recent_ts, "capsule": "unit-activity-fresh", "action": "test_run"}) + "\n",
        encoding="utf-8",
    )

    env = {
        **os.environ,
        "COS_VALIDATION_ACTIVITY_THRESHOLD": "60",
    }

    result = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{VALIDATION_LOCK}"; cos_validation_lock_active "{tmp_path}"',
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"Expected active (rc=0) for fresh activity but got {result.returncode}"
    )


# ── P5 race-window protection ─────────────────────────────────────────────────

def test_p5_cleanup_does_not_remove_young_lock(tmp_path: Path) -> None:
    """P5 race-window: cleanup hook must NOT remove a lock started <60s ago,
    even if PID is dead — protects the narrow window where another session is
    writing its lock.
    """
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)

    # Use a dead PID (1 is always alive on Unix, use a clearly dead one).
    dead_pid = 99999999

    _write_lock(
        runtime,
        {
            "run_id": "unit-race-young",
            "pid": dead_pid,
            "expires_at_epoch": int(time.time()) + 600,
            "started_at_epoch": int(time.time()) - 10,  # only 10s old → inside race window
            "capsule_dir": str(tmp_path / "capsule"),
            "message": "race window protection test",
        },
    )

    lock_path = runtime / "validation-capsule.lock"

    result = subprocess.run(
        ["bash", str(CLEANUP_HOOK)],
        env={
            **os.environ,
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        },
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, f"Cleanup hook must always exit 0; got {result.returncode}"
    assert lock_path.exists(), (
        "Cleanup hook must NOT remove a lock started <60s ago (race-window protection)"
    )


# ── P5 schema check ───────────────────────────────────────────────────────────

def test_p5_cleanup_skips_lock_without_run_id_or_capsule_dir(tmp_path: Path) -> None:
    """P5 schema: locks missing run_id or capsule_dir are not validation-capsule
    locks — cleanup hook must skip them (not remove, not classify as stale).
    """
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)

    # A lock without run_id and capsule_dir — foreign schema.
    _write_lock(
        runtime,
        {
            "pid": os.getpid(),
            "expires_at_epoch": int(time.time()) - 600,  # expired — would be stale if in-scope
            "started_at_epoch": int(time.time()) - 300,
            "message": "foreign lock — no run_id/capsule_dir",
        },
    )

    lock_path = runtime / "validation-capsule.lock"

    result = subprocess.run(
        ["bash", str(CLEANUP_HOOK)],
        env={
            **os.environ,
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        },
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0
    assert lock_path.exists(), (
        "Cleanup hook must skip locks that lack run_id/capsule_dir (foreign schema)"
    )


# ── Backward compat: legacy lock (no heartbeat fields) ───────────────────────

def test_legacy_lock_without_heartbeat_fields_falls_back_to_ttl_and_pid(tmp_path: Path) -> None:
    """Backward compat: lock written before ADR-113 (no heartbeat fields)
    must still be handled via TTL and PID checks — no regression.
    """
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)

    # Legacy schema: no last_heartbeat_epoch / heartbeat_interval_seconds
    _write_lock(
        runtime,
        {
            "run_id": "unit-legacy",
            "pid": os.getpid(),  # live PID
            "expires_at_epoch": int(time.time()) + 600,
            "started_at_epoch": int(time.time()) - 60,
            "message": "legacy lock compat test",
        },
    )

    result = _call_lock_active(tmp_path)

    # Should be treated as active (live PID + valid TTL) despite no heartbeat fields.
    assert result.returncode == 0, (
        f"Legacy lock (no heartbeat fields) with live PID must be treated as active; "
        f"got rc={result.returncode}"
    )
