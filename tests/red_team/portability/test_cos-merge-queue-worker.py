"""
Portability proofs for scripts/cos-merge-queue-worker.sh — P2.2 (ADR-116).

Git operations are mocked via a fake ``git`` binary on PATH.
3 proofs:
1. Dry-run mode (COS_MERGE_QUEUE_DRY=1) reads queue, prints intent, skips git.
2. Gate failure (ancestry check) marks entry as failed and exits non-zero.
3. Worker exits 2 (lock held) when another process holds the queue lock.
"""

from __future__ import annotations

import fcntl
import os
import stat
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKER_SCRIPT = REPO_ROOT / "scripts" / "cos-merge-queue-worker.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_git(tmp_path: Path, *, ancestry_fails: bool = False) -> Path:
    """Write a fake ``git`` executable into *tmp_path/bin*."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    git_bin = bin_dir / "git"

    # ancestry_fails controls whether ``merge-base --is-ancestor`` returns 1.
    ancestry_exit = "1" if ancestry_fails else "0"

    git_bin.write_text(
        textwrap.dedent(f"""\
        #!/usr/bin/env bash
        # Fake git for portability testing
        case "$1 $2" in
            "fetch origin") exit 0 ;;
            "merge-base --is-ancestor") exit {ancestry_exit} ;;
            "checkout main") exit 0 ;;
            "merge --ff-only") exit 0 ;;
            "push origin") exit 0 ;;
            "branch -d") exit 0 ;;
        esac
        # Default: delegate some common read queries to real git
        case "$1" in
            rev-parse|status|log) exec /usr/bin/git "$@" ;;
        esac
        exit 0
        """)
    )
    git_bin.chmod(git_bin.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return bin_dir


def _run_worker(
    tmp_path: Path,
    queue_file: Path,
    *,
    fake_git_dir: Path | None = None,
    dry_run: bool = False,
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["MERGE_QUEUE_PATH"] = str(queue_file)
    env["REPO_ROOT"] = str(REPO_ROOT)
    env["COGNITIVE_OS_SESSION_ID"] = "worker-test"
    # Skip pytest smoke gate — portability tests only exercise queue/git logic.
    env["COS_SKIP_SMOKE"] = "1"
    if dry_run:
        env["COS_MERGE_QUEUE_DRY"] = "1"
    if fake_git_dir:
        env["PATH"] = f"{fake_git_dir}:{env['PATH']}"
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        ["bash", str(WORKER_SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Proof 1: dry-run mode
# ---------------------------------------------------------------------------


class TestDryRunMode:
    """COS_MERGE_QUEUE_DRY=1 reads entry, prints what it would do, skips git."""

    def test_dry_run_prints_intent(self, tmp_path):
        queue_file = tmp_path / "q.jsonl"
        sys.path.insert(0, str(REPO_ROOT))
        from lib.merge_queue import enqueue  # noqa: PLC0415

        enqueue("session/dry-test", "dry-session", queue_path=queue_file)

        result = _run_worker(tmp_path, queue_file, dry_run=True)

        assert result.returncode == 0, f"Worker stderr:\n{result.stderr}"
        combined = result.stdout + result.stderr
        assert "DRY-RUN" in combined or "dry" in combined.lower(), (
            "Expected dry-run output, got:\n" + combined
        )
        # Queue entry should NOT be marked completed (dry-run = no writes).
        from lib.merge_queue import list_pending  # noqa: PLC0415

        pending = list_pending(queue_path=queue_file)
        assert len(pending) == 1, "Dry-run should not consume queue entries"

    def test_dry_run_empty_queue(self, tmp_path):
        queue_file = tmp_path / "empty.jsonl"
        result = _run_worker(tmp_path, queue_file, dry_run=True)
        assert result.returncode == 0
        assert "empty" in (result.stdout + result.stderr).lower()


# ---------------------------------------------------------------------------
# Proof 2: ancestry gate failure marks entry failed
# ---------------------------------------------------------------------------


class TestAncestryGateFailure:
    """When the ancestry gate fails the entry is marked 'failed'."""

    def test_gate_fail_marks_failed(self, tmp_path):
        queue_file = tmp_path / "q.jsonl"
        sys.path.insert(0, str(REPO_ROOT))
        from lib.merge_queue import enqueue, status  # noqa: PLC0415

        eid = enqueue("session/gate-fail", "gate-session", queue_path=queue_file)

        fake_git = _make_fake_git(tmp_path, ancestry_fails=True)
        result = _run_worker(tmp_path, queue_file, fake_git_dir=fake_git)

        # Worker should exit non-zero.
        assert result.returncode != 0, (
            f"Expected non-zero exit on gate failure, got 0.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        entry = status(eid, queue_path=queue_file)
        assert entry is not None
        assert entry["status"] == "failed", (
            f"Expected status=failed, got {entry['status']}"
        )


# ---------------------------------------------------------------------------
# Proof 3: lock contention exits with code 2
# ---------------------------------------------------------------------------


class TestLockContention:
    """Worker exits 2 when the queue lock is already held."""

    def test_exit_2_when_locked(self, tmp_path):
        queue_file = tmp_path / "q.jsonl"
        lock_file = queue_file.with_suffix(".worker.lock")
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.touch()

        # Hold the lock in this process.
        with lock_file.open("a") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                result = _run_worker(tmp_path, queue_file)
                assert result.returncode == 2, (
                    f"Expected exit 2 (lock held), got {result.returncode}.\n"
                    f"stdout: {result.stdout}\nstderr: {result.stderr}"
                )
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)
