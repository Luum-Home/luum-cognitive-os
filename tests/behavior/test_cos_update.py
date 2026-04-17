"""Behavior tests for the idempotent cos-update.sh (UX6).

Covers:
- Syntax is valid (bash -n)
- --help names the new capabilities (idempotent, verify, rollback)
- --dry-run is idempotent (same output on re-run)
- --dry-run does not mutate the tree
- A live update run creates a backup under .cognitive-os/backups/
- Backup rotation keeps only the last MAX_BACKUPS entries

Live-run tests operate on a scratch copy of the minimum project surface
(scripts/, hooks/, rules/, skills/, cognitive-os.yaml, etc.) inside tmp_path
so they cannot affect the real project.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPDATE_SCRIPT = PROJECT_ROOT / "scripts" / "cos-update.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_update(
    args: Optional[List[str]] = None,
    cwd: Optional[Path] = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess:
    """Invoke cos-update.sh against the real or scratch project root."""
    work_dir = cwd if cwd is not None else PROJECT_ROOT
    script_path = work_dir / "scripts" / "cos-update.sh"
    cmd = ["bash", str(script_path)] + (args or [])
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(work_dir),
    )


def _hash_dir(path: Path) -> str:
    """Return a stable fingerprint of the files under `path`."""
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    for entry in sorted(path.rglob("*")):
        try:
            rel = entry.relative_to(path).as_posix()
        except ValueError:
            continue
        if entry.is_symlink():
            h.update(f"L:{rel}:{os.readlink(entry)}\n".encode())
        elif entry.is_file():
            h.update(f"F:{rel}:{entry.stat().st_size}\n".encode())
        elif entry.is_dir():
            h.update(f"D:{rel}\n".encode())
    return h.hexdigest()


def _make_scratch_project(tmp_path: Path) -> Path:
    """Create a minimal clone of luum-agent-os inside tmp_path.

    We symlink (not copy) most dirs to avoid multi-MB copies, but we copy
    the scripts/ dir because the test may invoke cos-update.sh with --force
    and we want to isolate writes.
    """
    scratch = tmp_path / "scratch-cos"
    scratch.mkdir()

    # Symlink large read-only trees back to the real project
    for name in ("skills", "rules", "squads", "templates", "agents", "customizations", "docs", "lib", "tests", "hooks"):
        src = PROJECT_ROOT / name
        if src.exists():
            (scratch / name).symlink_to(src)

    # Copy scripts (we invoke cos-update.sh via this path)
    shutil.copytree(PROJECT_ROOT / "scripts", scratch / "scripts")

    # Copy the top-level marker files the script expects
    for fname in ("cognitive-os.yaml", "env.example"):
        src = PROJECT_ROOT / fname
        if src.exists():
            shutil.copy(src, scratch / fname)

    # A minimal .claude/settings.json so verification snapshot has something to hash
    claude_dir = scratch / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text('{"hooks": {}}')

    # An empty .cognitive-os/ so the backup dir can be created
    (scratch / ".cognitive-os").mkdir()

    # A compose file stub so docker checks gracefully skip (no docker in test env)
    compose_path = scratch / "docker-compose.cognitive-os.yml"
    if not compose_path.exists():
        compose_path.write_text("services: {}\n")

    return scratch


# ---------------------------------------------------------------------------
# Tests — pure inspection
# ---------------------------------------------------------------------------


def test_syntax_valid():
    """bash -n should pass on cos-update.sh."""
    result = subprocess.run(
        ["bash", "-n", str(UPDATE_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Syntax check failed:\n{result.stderr}"


def test_help_mentions_features():
    """--help must surface idempotent, verify, rollback capabilities."""
    result = _run_update(["--help"])
    assert result.returncode == 0, f"--help failed: {result.stderr}"
    combined = (result.stdout + result.stderr).lower()
    for token in ("idempotent", "verify", "rollback"):
        assert token in combined, f"--help output missing '{token}'"


def test_help_lists_flags():
    """--help must document the five new flags."""
    result = _run_update(["--help"])
    combined = result.stdout + result.stderr
    for flag in ("--dry-run", "--auto-rollback", "--no-verify", "--force", "--pull-images"):
        assert flag in combined, f"--help missing flag {flag}"


# ---------------------------------------------------------------------------
# Tests — idempotence of --dry-run
# ---------------------------------------------------------------------------


def test_update_idempotent():
    """Running --dry-run twice must yield identical stdout."""
    first = _run_update(["--dry-run"])
    second = _run_update(["--dry-run"])

    assert first.returncode == 0, f"First dry-run failed: {first.stderr}"
    assert second.returncode == 0, f"Second dry-run failed: {second.stderr}"
    assert first.stdout == second.stdout, (
        "Two --dry-run invocations produced different stdout — not idempotent"
    )


def test_update_dry_run_no_changes(tmp_path):
    """--dry-run must not mutate the tree (no backup created, no files changed)."""
    scratch = _make_scratch_project(tmp_path)

    before = _hash_dir(scratch / ".cognitive-os")
    before_claude = _hash_dir(scratch / ".claude")

    result = _run_update(["--dry-run"], cwd=scratch)
    assert result.returncode == 0, f"dry-run failed: {result.stderr}"

    after = _hash_dir(scratch / ".cognitive-os")
    after_claude = _hash_dir(scratch / ".claude")

    assert before == after, ".cognitive-os/ changed during --dry-run"
    assert before_claude == after_claude, ".claude/ changed during --dry-run"

    backup_root = scratch / ".cognitive-os" / "backups"
    if backup_root.exists():
        assert not any(backup_root.iterdir()), "Backups must not be created in --dry-run"


# ---------------------------------------------------------------------------
# Tests — backup creation and rotation (live runs in scratch dir)
# ---------------------------------------------------------------------------


def test_update_creates_backup(tmp_path):
    """After a non-dry-run, .cognitive-os/backups/pre-update-<ts>/ must exist."""
    scratch = _make_scratch_project(tmp_path)

    # --no-verify + --force to skip the heavy verification but still exercise
    # the backup path. --force also bypasses the idempotence short-circuit so
    # the backup is created unconditionally.
    result = _run_update(["--no-verify", "--force"], cwd=scratch, timeout=90)
    # Allow non-zero (docker unavailable etc.); we only care that backup exists.
    # Exit code 2 means verify failed, but we passed --no-verify so shouldn't happen.
    # Exit code 1 means apply failed — still acceptable for the backup-creation
    # assertion because backup is created BEFORE apply.
    assert result.returncode in (0, 1), (
        f"Unexpected exit code {result.returncode}. stderr: {result.stderr[-500:]}"
    )

    backup_root = scratch / ".cognitive-os" / "backups"
    assert backup_root.exists(), f".cognitive-os/backups/ not created. stdout: {result.stdout[-500:]}"

    backups = [p for p in backup_root.iterdir() if p.is_dir() and p.name.startswith("pre-update-")]
    assert len(backups) >= 1, (
        f"No pre-update-* backup created. Contents: {list(backup_root.iterdir())}"
    )

    # Backup must contain at least meta.txt
    assert (backups[0] / "meta.txt").exists(), "meta.txt missing from backup"


def test_update_backup_rotation(tmp_path):
    """After more than MAX_BACKUPS runs, only the last 3 backups must remain."""
    scratch = _make_scratch_project(tmp_path)
    backup_root = scratch / ".cognitive-os" / "backups"

    # Seed 5 fake older backups so rotation can prune them in one live run.
    # We use sortable ISO-like timestamps so newer > older lexically.
    older_stamps = [
        "20260101T010000Z",
        "20260102T010000Z",
        "20260103T010000Z",
        "20260104T010000Z",
        "20260105T010000Z",
    ]
    backup_root.mkdir(parents=True, exist_ok=True)
    for stamp in older_stamps:
        d = backup_root / f"pre-update-{stamp}"
        d.mkdir()
        (d / "meta.txt").write_text(f"timestamp_utc={stamp}\n")

    # Run live (non-dry) so rotation fires. Short-circuits at snapshot
    # short-circuit MUST NOT prevent rotation, so use --force.
    result = _run_update(["--no-verify", "--force"], cwd=scratch, timeout=90)
    assert result.returncode in (0, 1), (
        f"Unexpected exit code {result.returncode}. stderr: {result.stderr[-500:]}"
    )

    # After the run there are the 5 seeds + 1 new. Rotation must keep only 3.
    remaining = sorted(
        p.name for p in backup_root.iterdir()
        if p.is_dir() and p.name.startswith("pre-update-")
    )
    assert len(remaining) == 3, (
        f"Expected 3 backups after rotation, got {len(remaining)}: {remaining}"
    )

    # The three kept must be the lexically greatest (newest by ISO timestamp).
    # The run created one backup with a fresh timestamp — it should be the newest.
    # The two next-newest from the seed (20260105, 20260104) must survive.
    assert any("20260105" in name for name in remaining), (
        f"Newest seed (20260105) was rotated out incorrectly: {remaining}"
    )
    assert any("20260104" in name for name in remaining), (
        f"Second-newest seed (20260104) was rotated out incorrectly: {remaining}"
    )
    # Oldest three seeds must be gone
    for stamp in ("20260101", "20260102", "20260103"):
        assert not any(stamp in name for name in remaining), (
            f"Old seed {stamp} survived rotation: {remaining}"
        )
