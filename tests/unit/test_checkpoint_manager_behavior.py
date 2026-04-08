"""
Behavioral tests for lib/checkpoint_manager.py.

Covers:
  - restore_stash with a nonexistent checkpoint_id returns False (no crash)
  - should_checkpoint respects the configured interval
  - A future timestamp in the marker file causes should_checkpoint to skip
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib.checkpoint_manager import CheckpointManager

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with an initial commit."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    readme = tmp_path / "README.md"
    readme.write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    return tmp_path


def _make_manager(project_dir: Path, interval_minutes: int = 5) -> CheckpointManager:
    """Return a CheckpointManager scoped to project_dir."""
    return CheckpointManager(
        checkpoint_dir=".cognitive-os/checkpoints",
        interval_minutes=interval_minutes,
        project_dir=str(project_dir),
    )


# ---------------------------------------------------------------------------
# restore_stash with nonexistent ID
# ---------------------------------------------------------------------------


class TestRestoreNonexistentStash:
    def test_restore_nonexistent_returns_false(self, git_repo):
        """restore_stash with a made-up checkpoint_id must return False and not raise.

        There is no matching stash entry for the given ID, so the function
        must gracefully return False rather than crashing or raising an exception.
        """
        manager = _make_manager(git_repo)
        result = manager.restore_stash("cos-99991231-000000-definitely-not-here")
        assert result is False, (
            "restore_stash must return False when no matching stash entry exists"
        )


# ---------------------------------------------------------------------------
# should_checkpoint respects interval
# ---------------------------------------------------------------------------


class TestShouldCheckpointInterval:
    def test_should_checkpoint_respects_interval(self, tmp_path):
        """should_checkpoint must return False when elapsed time < interval.

        Pass a last_checkpoint_time that is (interval - 1) seconds in the past.
        The manager should NOT request a checkpoint yet.
        """
        interval_minutes = 5
        manager = _make_manager(tmp_path, interval_minutes=interval_minutes)

        # Just under the interval — 1 second before threshold
        elapsed_seconds = interval_minutes * 60 - 1
        last_checkpoint = datetime.now(timezone.utc) - timedelta(seconds=elapsed_seconds)

        result = manager.should_checkpoint(last_checkpoint_time=last_checkpoint)
        assert result is False, (
            f"should_checkpoint returned True after only {elapsed_seconds}s "
            f"(interval is {interval_minutes * 60}s)"
        )

    def test_should_checkpoint_triggers_after_interval(self, tmp_path):
        """should_checkpoint must return True when elapsed time >= interval.

        Pass a last_checkpoint_time that is exactly interval seconds in the past.
        """
        interval_minutes = 5
        manager = _make_manager(tmp_path, interval_minutes=interval_minutes)

        # Exactly at the interval boundary
        elapsed_seconds = interval_minutes * 60
        last_checkpoint = datetime.now(timezone.utc) - timedelta(seconds=elapsed_seconds)

        result = manager.should_checkpoint(last_checkpoint_time=last_checkpoint)
        assert result is True, (
            f"should_checkpoint should return True after exactly {elapsed_seconds}s "
            f"(interval is {interval_minutes * 60}s)"
        )


# ---------------------------------------------------------------------------
# Future timestamp in marker file
# ---------------------------------------------------------------------------


class TestFutureTimestampSkips:
    def test_future_timestamp_skips(self, tmp_path):
        """A marker file with a future epoch timestamp must cause should_checkpoint to return False.

        If the marker file somehow has a future timestamp (e.g., clock skew or
        manual tampering), the manager should interpret it as "just checkpointed"
        and skip the checkpoint.
        """
        interval_minutes = 5
        manager = _make_manager(tmp_path, interval_minutes=interval_minutes)

        # Write a future timestamp (1 hour from now) to the marker file
        marker_dir = Path(tmp_path) / ".cognitive-os" / "checkpoints"
        marker_dir.mkdir(parents=True, exist_ok=True)
        marker_file = marker_dir / ".last-checkpoint"
        future_epoch = int(time.time()) + 3600  # 1 hour in the future
        marker_file.write_text(str(future_epoch))

        result = manager.should_checkpoint()
        assert result is False, (
            "A future marker timestamp means no checkpoint is needed yet — "
            f"should_checkpoint should return False, got {result}"
        )
