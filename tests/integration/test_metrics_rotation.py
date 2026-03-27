"""Integration tests for metrics-rotation.sh.

Tests file truncation, archive creation, gzip validity, old archive cleanup,
and small file passthrough.
Migrated from test-metrics-rotation.sh.
"""

import gzip
import json
import os
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture
def project_root():
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def rotation_env(tmp_path, project_root):
    """Create a temporary project with rotation-compatible metrics directory."""
    project_dir = tmp_path / "project"
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)

    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        "COGNITIVE_OS_SESSION_ID": "",
        "COGNITIVE_OS_METRICS_MAX_LINES": "5000",
        "COGNITIVE_OS_METRICS_KEEP_LINES": "2500",
        "COGNITIVE_OS_METRICS_RETENTION_DAYS": "30",
    }

    return {
        "project_dir": project_dir,
        "metrics_dir": metrics_dir,
        "env": env,
        "rotation_script": project_root / "hooks" / "metrics-rotation.sh",
    }


def _generate_jsonl(filepath: Path, count: int):
    """Write count lines of JSONL data."""
    with open(filepath, "w") as f:
        for i in range(1, count + 1):
            f.write(json.dumps({"line": i, "ts": "2025-01-01T00:00:00Z"}) + "\n")


@pytest.mark.integration
class TestMetricsRotation:
    """Tests for the metrics rotation script."""

    def test_rotation_truncates_to_keep_lines(self, rotation_env):
        script = rotation_env["rotation_script"]
        if not script.exists():
            pytest.skip("metrics-rotation.sh not found")

        metrics_file = rotation_env["metrics_dir"] / "test-rotation.jsonl"
        _generate_jsonl(metrics_file, 6000)

        lines_before = len(metrics_file.read_text().strip().split("\n"))
        assert lines_before == 6000

        subprocess.run(
            ["bash", str(script)],
            env=rotation_env["env"],
            capture_output=True,
            timeout=30,
        )

        lines_after = len(metrics_file.read_text().strip().split("\n"))
        assert lines_after == 2500, f"expected 2500 lines after rotation, got {lines_after}"

        # Verify the kept lines are the most recent (last 2500)
        first_line = json.loads(metrics_file.read_text().strip().split("\n")[0])
        assert first_line["line"] == 3501, f"first kept line should be 3501, got {first_line['line']}"

    def test_archive_directory_created(self, rotation_env):
        script = rotation_env["rotation_script"]
        if not script.exists():
            pytest.skip("metrics-rotation.sh not found")

        metrics_file = rotation_env["metrics_dir"] / "test-archive.jsonl"
        _generate_jsonl(metrics_file, 6000)

        subprocess.run(
            ["bash", str(script)],
            env=rotation_env["env"],
            capture_output=True,
            timeout=30,
        )

        archive_dir = rotation_env["metrics_dir"] / ".archive"
        assert archive_dir.is_dir(), "archive directory should be created"

        archives = list(archive_dir.glob("test-archive-*.jsonl.gz"))
        assert len(archives) == 1, f"expected 1 archive file, got {len(archives)}"

    def test_archive_is_valid_gzip(self, rotation_env):
        script = rotation_env["rotation_script"]
        if not script.exists():
            pytest.skip("metrics-rotation.sh not found")

        metrics_file = rotation_env["metrics_dir"] / "test-gzip.jsonl"
        _generate_jsonl(metrics_file, 6000)

        subprocess.run(
            ["bash", str(script)],
            env=rotation_env["env"],
            capture_output=True,
            timeout=30,
        )

        archive_dir = rotation_env["metrics_dir"] / ".archive"
        gz_files = list(archive_dir.glob("test-gzip-*.jsonl.gz"))
        assert len(gz_files) > 0, "gzip archive should exist"

        gz_file = gz_files[0]
        with gzip.open(gz_file, "rt") as f:
            archived_lines = f.read().strip().split("\n")

        assert len(archived_lines) == 3500, (
            f"archive should contain 3500 lines, got {len(archived_lines)}"
        )

    def test_old_archive_deleted(self, rotation_env):
        script = rotation_env["rotation_script"]
        if not script.exists():
            pytest.skip("metrics-rotation.sh not found")

        archive_dir = rotation_env["metrics_dir"] / ".archive"
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Create an old archive (40 days old)
        old_archive = archive_dir / "old-metrics-20240101-000000.jsonl.gz"
        with gzip.open(old_archive, "wt") as f:
            f.write("old data\n")

        # Set mtime to 40 days ago
        old_mtime = time.time() - (40 * 86400)
        os.utime(old_archive, (old_mtime, old_mtime))

        # Create a file that triggers rotation
        trigger = rotation_env["metrics_dir"] / "trigger.jsonl"
        _generate_jsonl(trigger, 6000)

        subprocess.run(
            ["bash", str(script)],
            env=rotation_env["env"],
            capture_output=True,
            timeout=30,
        )

        assert not old_archive.exists(), "old archive (40 days) should be deleted"

    def test_small_files_untouched(self, rotation_env):
        script = rotation_env["rotation_script"]
        if not script.exists():
            pytest.skip("metrics-rotation.sh not found")

        metrics_file = rotation_env["metrics_dir"] / "small.jsonl"
        _generate_jsonl(metrics_file, 100)

        subprocess.run(
            ["bash", str(script)],
            env=rotation_env["env"],
            capture_output=True,
            timeout=30,
        )

        lines = len(metrics_file.read_text().strip().split("\n"))
        assert lines == 100, f"small file should stay at 100 lines, got {lines}"

        archive_dir = rotation_env["metrics_dir"] / ".archive"
        small_archives = list(archive_dir.glob("small-*.gz")) if archive_dir.exists() else []
        assert len(small_archives) == 0, "no archive should be created for small files"
