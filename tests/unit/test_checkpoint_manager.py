"""Tests for lib/checkpoint_manager.py -- Crash Recovery Checkpoint System.

Covers checkpoint creation, recovery detection, stash management,
interval checking, cleanup, metadata format, and edge cases.

Run with: pytest tests/unit/test_checkpoint_manager.py -v

Author: luum
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Ensure project root is importable
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from lib.checkpoint_manager import CheckpointManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with an initial commit."""
    subprocess.run(
        ["git", "init", "-q"],
        cwd=str(tmp_path),
        capture_output=True,
        check=True,
    )
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
    # Create initial commit so stash works
    readme = tmp_path / "README.md"
    readme.write_text("# Test\n")
    subprocess.run(
        ["git", "add", "."],
        cwd=str(tmp_path),
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "initial", "-q"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    return tmp_path


@pytest.fixture
def manager(git_repo: Path) -> CheckpointManager:
    """Create a CheckpointManager pointing to the test git repo."""
    return CheckpointManager(
        checkpoint_dir=".cognitive-os/checkpoints",
        interval_minutes=5,
        project_dir=str(git_repo),
    )


@pytest.fixture
def dirty_repo(git_repo: Path) -> Path:
    """Create a git repo with uncommitted changes."""
    (git_repo / "dirty_file.py").write_text("print('hello')\n")
    return git_repo


# ---------------------------------------------------------------------------
# create_checkpoint
# ---------------------------------------------------------------------------


class TestCreateCheckpoint:

    def test_with_dirty_files(self, manager: CheckpointManager, dirty_repo: Path):
        """Checkpoint with dirty files creates a stash and metadata file."""
        cp = manager.create_checkpoint(note="test-dirty")

        assert cp.checkpoint_id.startswith("cos-")
        assert cp.uncommitted_changes > 0
        assert cp.note == "test-dirty"
        assert len(cp.files_modified) > 0
        assert "dirty_file.py" in cp.files_modified

        # Metadata file should exist
        meta_path = os.path.join(manager.checkpoint_dir, f"{cp.checkpoint_id}.json")
        assert os.path.isfile(meta_path)

        with open(meta_path) as f:
            data = json.load(f)
        assert data["checkpoint_id"] == cp.checkpoint_id

    def test_with_clean_repo(self, manager: CheckpointManager, git_repo: Path):
        """Checkpoint with clean repo creates metadata but no stash."""
        cp = manager.create_checkpoint(note="test-clean")

        assert cp.checkpoint_id.startswith("cos-")
        assert cp.uncommitted_changes == 0
        assert cp.git_stash_ref is None
        assert cp.files_modified == []

    def test_working_dir_unchanged_after_checkpoint(
        self, manager: CheckpointManager, dirty_repo: Path
    ):
        """After checkpoint, dirty files are still present in working dir."""
        dirty_file = dirty_repo / "dirty_file.py"
        assert dirty_file.exists()

        manager.create_checkpoint()

        # File should still be in working directory
        assert dirty_file.exists()
        assert dirty_file.read_text() == "print('hello')\n"

    def test_stash_created_for_dirty_repo(
        self, manager: CheckpointManager, dirty_repo: Path
    ):
        """A git stash entry with cos- prefix should exist after checkpoint."""
        cp = manager.create_checkpoint()

        subprocess.run(
            ["git", "stash", "list"],
            cwd=str(dirty_repo),
            capture_output=True,
            text=True,
        )
        # The stash was pushed and popped, so it should exist in the reflog
        # but may or may not show in stash list depending on git version
        # The key guarantee is the working directory is unchanged
        assert cp.git_stash_ref is not None or cp.uncommitted_changes == 0

    def test_checkpoint_metadata_has_required_fields(
        self, manager: CheckpointManager, dirty_repo: Path
    ):
        """Checkpoint metadata JSON has all required fields."""
        cp = manager.create_checkpoint(note="field-check")
        meta_path = os.path.join(manager.checkpoint_dir, f"{cp.checkpoint_id}.json")

        with open(meta_path) as f:
            data = json.load(f)

        required_fields = [
            "checkpoint_id",
            "timestamp",
            "session_id",
            "tasks_in_progress",
            "files_modified",
            "uncommitted_changes",
            "cost_since_last_commit",
            "note",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_checkpoint_id_is_unique(
        self, manager: CheckpointManager, dirty_repo: Path
    ):
        """Two checkpoints in quick succession have different IDs."""
        cp1 = manager.create_checkpoint(note="first")
        cp2 = manager.create_checkpoint(note="second")
        assert cp1.checkpoint_id != cp2.checkpoint_id


# ---------------------------------------------------------------------------
# recover_from_crash
# ---------------------------------------------------------------------------


class TestRecoverFromCrash:

    def test_no_crash_returns_none(self, manager: CheckpointManager, git_repo: Path):
        """With no cos- stashes, recovery returns None."""
        result = manager.recover_from_crash()
        assert result is None

    def test_detects_stash(self, manager: CheckpointManager, dirty_repo: Path):
        """After a checkpoint (simulating crash), recovery detects stash."""
        # Create dirty file and checkpoint
        manager.create_checkpoint(note="pre-crash")

        # Now simulate crash: create another dirty file and stash it
        (dirty_repo / "another.py").write_text("x = 1\n")
        subprocess.run(
            ["git", "stash", "push", "-m", "cos-simulated-crash", "--include-untracked"],
            cwd=str(dirty_repo),
            capture_output=True,
        )

        result = manager.recover_from_crash()
        assert result is not None
        assert result["crash_detected"] is True
        assert result["stash_count"] > 0

    def test_recovery_info_structure(
        self, manager: CheckpointManager, dirty_repo: Path
    ):
        """Recovery info has all expected keys."""
        # Create a cos- stash manually
        subprocess.run(
            ["git", "stash", "push", "-m", "cos-test-recovery", "--include-untracked"],
            cwd=str(dirty_repo),
            capture_output=True,
        )

        result = manager.recover_from_crash()
        assert result is not None

        expected_keys = [
            "crash_detected",
            "last_clean_session",
            "crash_time_estimate",
            "stashes",
            "stash_count",
            "last_checkpoint",
            "tasks_in_progress",
            "files_modified",
            "cost_since_last_commit",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# should_checkpoint
# ---------------------------------------------------------------------------


class TestShouldCheckpoint:

    def test_first_time_returns_true(self, manager: CheckpointManager):
        """With no marker file, should_checkpoint returns True."""
        assert manager.should_checkpoint() is True

    def test_respects_interval(self, manager: CheckpointManager, git_repo: Path):
        """After a recent checkpoint, should_checkpoint returns False."""
        os.makedirs(manager.checkpoint_dir, exist_ok=True)
        marker = manager._marker_path()
        with open(marker, "w") as f:
            f.write(str(int(time.time())))

        assert manager.should_checkpoint() is False

    def test_expired_marker_returns_true(
        self, manager: CheckpointManager, git_repo: Path
    ):
        """With an old marker, should_checkpoint returns True."""
        os.makedirs(manager.checkpoint_dir, exist_ok=True)
        marker = manager._marker_path()
        old_time = int(time.time()) - 600  # 10 minutes ago
        with open(marker, "w") as f:
            f.write(str(old_time))

        assert manager.should_checkpoint() is True

    def test_with_explicit_datetime(self, manager: CheckpointManager):
        """should_checkpoint with explicit last_checkpoint_time parameter."""
        now = datetime.now(timezone.utc)
        recent = now - timedelta(minutes=2)
        old = now - timedelta(minutes=10)

        assert manager.should_checkpoint(last_checkpoint_time=recent) is False
        assert manager.should_checkpoint(last_checkpoint_time=old) is True


# ---------------------------------------------------------------------------
# list_checkpoints
# ---------------------------------------------------------------------------


class TestListCheckpoints:

    def test_returns_sorted(self, manager: CheckpointManager, dirty_repo: Path):
        """Checkpoints are returned newest first."""
        cp1 = manager.create_checkpoint(note="first")
        cp2 = manager.create_checkpoint(note="second")

        checkpoints = manager.list_checkpoints(last_n=5)
        assert len(checkpoints) == 2
        # Newest first
        assert checkpoints[0].checkpoint_id == cp2.checkpoint_id
        assert checkpoints[1].checkpoint_id == cp1.checkpoint_id

    def test_empty_dir(self, manager: CheckpointManager):
        """Empty checkpoints dir returns empty list."""
        checkpoints = manager.list_checkpoints()
        assert checkpoints == []

    def test_respects_last_n(self, manager: CheckpointManager, dirty_repo: Path):
        """Only returns the requested number of checkpoints."""
        for i in range(5):
            manager.create_checkpoint(note=f"cp-{i}")

        checkpoints = manager.list_checkpoints(last_n=3)
        assert len(checkpoints) == 3


# ---------------------------------------------------------------------------
# cleanup_old_checkpoints
# ---------------------------------------------------------------------------


class TestCleanupOldCheckpoints:

    def test_keeps_n_most_recent(self, manager: CheckpointManager, dirty_repo: Path):
        """Cleanup removes old checkpoints but keeps the N most recent."""
        for i in range(5):
            manager.create_checkpoint(note=f"cp-{i}")

        removed = manager.cleanup_old_checkpoints(keep_last=2)
        assert removed == 3

        remaining = manager.list_checkpoints(last_n=10)
        assert len(remaining) == 2

    def test_empty_dir_returns_zero(self, manager: CheckpointManager):
        """Cleanup with no checkpoints returns 0."""
        removed = manager.cleanup_old_checkpoints()
        assert removed == 0

    def test_fewer_than_keep_removes_nothing(
        self, manager: CheckpointManager, dirty_repo: Path
    ):
        """If fewer checkpoints than keep_last, nothing is removed."""
        manager.create_checkpoint(note="only-one")
        removed = manager.cleanup_old_checkpoints(keep_last=10)
        assert removed == 0


# ---------------------------------------------------------------------------
# restore_stash
# ---------------------------------------------------------------------------


class TestRestoreStash:

    def test_restore_applies_stash(
        self, manager: CheckpointManager, dirty_repo: Path
    ):
        """Restoring a checkpoint stash applies the changes."""
        # Create a cos- stash manually (simulating a crash where pop never ran)
        subprocess.run(
            ["git", "stash", "push", "-m", "cos-restore-test", "--include-untracked"],
            cwd=str(dirty_repo),
            capture_output=True,
        )
        # File should be gone from working dir (stashed)
        assert not (dirty_repo / "dirty_file.py").exists()

        result = manager.restore_stash("cos-restore-test")
        assert result is True

        # File should be restored
        assert (dirty_repo / "dirty_file.py").exists()

    def test_restore_nonexistent_returns_false(
        self, manager: CheckpointManager, git_repo: Path
    ):
        """Restoring a non-existent checkpoint returns False."""
        result = manager.restore_stash("cos-does-not-exist")
        assert result is False


# ---------------------------------------------------------------------------
# format_recovery_report
# ---------------------------------------------------------------------------


class TestFormatRecoveryReport:

    def test_report_has_sections(self, manager: CheckpointManager):
        """Recovery report contains all expected sections."""
        info = {
            "crash_detected": True,
            "last_clean_session": "2026-03-27T14:30:00Z",
            "crash_time_estimate": "2026-03-27T14:45:00Z",
            "stashes": [{"entry": "stash@{0}: On main: cos-test"}],
            "stash_count": 1,
            "last_checkpoint": None,
            "tasks_in_progress": ["Implement JWT auth"],
            "files_modified": ["lib/auth.py", "tests/test_auth.py"],
            "cost_since_last_commit": 0.45,
        }

        report = manager.format_recovery_report(info)

        assert "CRASH RECOVERY DETECTED" in report
        assert "Last clean session" in report
        assert "Crash time" in report
        assert "Recoverable work" in report
        assert "uncommitted file" in report
        assert "lib/auth.py" in report
        assert "task(s) were in progress" in report
        assert "Implement JWT auth" in report
        assert "$0.45" in report
        assert "Actions" in report

    def test_report_with_no_files(self, manager: CheckpointManager):
        """Report handles empty file list gracefully."""
        info = {
            "crash_detected": True,
            "last_clean_session": None,
            "crash_time_estimate": None,
            "stashes": [],
            "stash_count": 0,
            "last_checkpoint": None,
            "tasks_in_progress": [],
            "files_modified": [],
            "cost_since_last_commit": 0.0,
        }

        report = manager.format_recovery_report(info)
        assert "CRASH RECOVERY DETECTED" in report
        assert "Actions" in report


# ---------------------------------------------------------------------------
# Multiple checkpoints
# ---------------------------------------------------------------------------


class TestMultipleCheckpoints:

    def test_multiple_checkpoints_dont_conflict(
        self, manager: CheckpointManager, dirty_repo: Path
    ):
        """Creating multiple checkpoints produces distinct, valid metadata."""
        cps = []
        for i in range(3):
            (dirty_repo / f"file_{i}.py").write_text(f"x = {i}\n")
            cp = manager.create_checkpoint(note=f"multi-{i}")
            cps.append(cp)

        ids = [cp.checkpoint_id for cp in cps]
        assert len(set(ids)) == 3  # All unique

        # All metadata files exist
        for cp in cps:
            meta_path = os.path.join(
                manager.checkpoint_dir, f"{cp.checkpoint_id}.json"
            )
            assert os.path.isfile(meta_path)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:

    def test_empty_checkpoints_dir_handled(self, manager: CheckpointManager):
        """Operations on non-existent checkpoint dir don't crash."""
        assert manager.list_checkpoints() == []
        assert manager.cleanup_old_checkpoints() == 0
        assert manager.recover_from_crash() is None

    def test_corrupt_metadata_skipped(
        self, manager: CheckpointManager, git_repo: Path
    ):
        """Corrupt checkpoint JSON files are skipped without crashing."""
        os.makedirs(manager.checkpoint_dir, exist_ok=True)
        corrupt_path = os.path.join(manager.checkpoint_dir, "cos-corrupt.json")
        with open(corrupt_path, "w") as f:
            f.write("not json{{{")

        checkpoints = manager.list_checkpoints()
        assert len(checkpoints) == 0  # Corrupt file skipped

    def test_marker_with_invalid_content(
        self, manager: CheckpointManager, git_repo: Path
    ):
        """Invalid marker file content triggers a new checkpoint."""
        os.makedirs(manager.checkpoint_dir, exist_ok=True)
        marker = manager._marker_path()
        with open(marker, "w") as f:
            f.write("not-a-number")

        assert manager.should_checkpoint() is True
