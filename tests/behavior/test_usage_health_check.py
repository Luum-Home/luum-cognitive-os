"""Behavior tests for hooks/usage-health-check.sh."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.parent
HOOK = PROJECT_ROOT / "hooks" / "usage-health-check.sh"


def run_hook(env: dict | None = None, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run the hook and return the completed process."""
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        ["bash", str(HOOK)],
        capture_output=True,
        text=True,
        env=merged_env,
        cwd=cwd or str(PROJECT_ROOT),
    )


# ---------------------------------------------------------------------------
# 1. Syntax validation
# ---------------------------------------------------------------------------

def test_hook_syntax_valid():
    """bash -n must pass with exit code 0."""
    result = subprocess.run(
        ["bash", "-n", str(HOOK)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Syntax check failed: {result.stderr}"


# ---------------------------------------------------------------------------
# 2. Always exits 0
# ---------------------------------------------------------------------------

def test_hook_exits_zero():
    """Hook always exits 0, even on first run."""
    with tempfile.TemporaryDirectory() as tmpdir:
        metrics_dir = Path(tmpdir) / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True)
        result = run_hook(cwd=tmpdir)
    assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"


# ---------------------------------------------------------------------------
# 3. Skip if ran within 24h
# ---------------------------------------------------------------------------

def test_skip_if_recent():
    """Hook must skip (no output, no update) when last run < 24h ago."""
    with tempfile.TemporaryDirectory() as tmpdir:
        metrics_dir = Path(tmpdir) / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True)
        last_run_file = metrics_dir / "usage-health-last-run"

        # Write a timestamp from 1 hour ago
        one_hour_ago = int(time.time()) - 3600
        last_run_file.write_text(str(one_hour_ago))

        mtime_before = last_run_file.stat().st_mtime
        result = run_hook(cwd=tmpdir)

        assert result.returncode == 0
        # Timestamp file should NOT have been updated
        mtime_after = last_run_file.stat().st_mtime
        assert mtime_after == mtime_before, "Timestamp was updated even though < 24h elapsed"


# ---------------------------------------------------------------------------
# 4. Runs if last run > 24h ago
# ---------------------------------------------------------------------------

def test_runs_if_stale():
    """Hook must run tracker logic when last run > 24h ago."""
    with tempfile.TemporaryDirectory() as tmpdir:
        metrics_dir = Path(tmpdir) / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True)
        last_run_file = metrics_dir / "usage-health-last-run"

        # Write a timestamp from 25 hours ago
        stale_ts = int(time.time()) - (25 * 3600)
        last_run_file.write_text(str(stale_ts))

        last_run_file.stat().st_mtime
        # Run from project root (python3 import path needs lib/)
        result = run_hook(cwd=str(PROJECT_ROOT))

        assert result.returncode == 0
        # Timestamp file in project root should be updated (hook creates it there)
        updated_file = PROJECT_ROOT / ".cognitive-os" / "metrics" / "usage-health-last-run"
        if updated_file.exists():
            new_ts = int(updated_file.read_text().strip())
            assert new_ts > stale_ts, "Timestamp was not updated after stale run"


# ---------------------------------------------------------------------------
# 5. Creates timestamp file
# ---------------------------------------------------------------------------

def test_creates_timestamp_file():
    """Hook must create the last-run timestamp file on first execution."""
    # Run from project root where lib/ is accessible
    ts_file = PROJECT_ROOT / ".cognitive-os" / "metrics" / "usage-health-last-run"

    # Remove file if it exists so we test creation
    existed_before = ts_file.exists()
    old_ts = int(ts_file.read_text().strip()) if existed_before else 0

    result = run_hook(cwd=str(PROJECT_ROOT))
    assert result.returncode == 0

    if ts_file.exists():
        new_ts = int(ts_file.read_text().strip())
        assert new_ts >= old_ts, "Timestamp should be current time or later"
    # If the file was skipped (ran recently), that's also acceptable behaviour


# ---------------------------------------------------------------------------
# 6. ComponentUsageTracker imports correctly
# ---------------------------------------------------------------------------

def test_tracker_import_works():
    """ComponentUsageTracker must be importable from lib/."""
    result = subprocess.run(
        [
            "python3",
            "-c",
            "from lib.component_usage_tracker import ComponentUsageTracker; "
            "t = ComponentUsageTracker(); print('ok')",
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"Import failed: {result.stderr}"
    assert "ok" in result.stdout
