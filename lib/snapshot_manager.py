"""
snapshot_manager.py — Pre-agent working-tree snapshot helpers.

Strategy (ADR-099):
  - Tracked-modified files: captured via `git stash push --keep-index` (no --include-untracked)
  - Untracked files: copied to .cognitive-os/snapshots/<snapshot-id>/ — NOT removed from WT
  - Manifest: .cognitive-os/snapshots/<snapshot-id>/manifest.json correlates both halves

This preserves the safety net (full rollback possible) without ghosting WT files.

Legacy mode: COS_LEGACY_SNAPSHOT=1 restores old behaviour (git stash --include-untracked).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

# ─── Constants ────────────────────────────────────────────────────────────────

DEFAULT_TTL_DAYS = 30
SNAPSHOTS_DIR_NAME = ".cognitive-os/snapshots"
MANIFEST_FILE = "manifest.json"

# ─── Internal helpers ─────────────────────────────────────────────────────────


def _run(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run a subprocess, return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _get_untracked_files(repo: Path) -> list[str]:
    """Return list of untracked files (relative to repo root), excluding .cognitive-os/."""
    rc, out, _ = _run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo,
    )
    if rc != 0 or not out:
        return []
    files = [f for f in out.splitlines() if f and not f.startswith(".cognitive-os/")]
    return files


def _has_tracked_modifications(repo: Path) -> bool:
    """Return True if there are tracked (staged or unstaged) modifications."""
    rc, out, _ = _run(
        ["git", "status", "--porcelain"],
        cwd=repo,
    )
    if rc != 0 or not out:
        return False
    for line in out.splitlines():
        if not line:
            continue
        # Status codes for tracked files: M, D, A, R, C, U
        # Untracked lines start with "??"
        if not line.startswith("??") and not line[3:].startswith(".cognitive-os/"):
            return True
    return False


def _stash_tracked(repo: Path, message: str) -> Optional[str]:
    """
    Run `git stash push --keep-index` (no --include-untracked) to stash
    tracked modifications. Returns the stash ref (e.g. "stash@{0}") or None.
    """
    rc, _, _ = _run(
        [
            "git",
            "stash",
            "push",
            "--keep-index",
            "-m",
            message,
            "--",
            ":(exclude).cognitive-os",
            ":(exclude).cognitive-os/**",
            ".",
        ],
        cwd=repo,
    )
    if rc != 0:
        return None
    rc2, out2, _ = _run(
        ["git", "stash", "list", "--max-count=1"],
        cwd=repo,
    )
    if rc2 != 0 or not out2:
        return None
    ref = out2.split(":")[0].strip()
    return ref if ref else None


def _copy_untracked(repo: Path, untracked: list[str], dest: Path) -> list[str]:
    """
    Copy untracked files from the WT to dest/, preserving directory structure.
    Returns list of paths successfully copied (relative to repo).
    """
    copied: list[str] = []
    for rel_path in untracked:
        src = repo / rel_path
        dst = dest / rel_path
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            copied.append(rel_path)
        except Exception:
            pass  # best-effort; partial copies are still useful
    return copied


# ─── Public API ───────────────────────────────────────────────────────────────


def create_snapshot(repo: Path, agent_id: str) -> dict:
    """
    Create a snapshot of the current working tree before an agent launch.

    Returns a manifest dict:
    {
        "snapshot_id": str,
        "agent_id": str,
        "timestamp": float (unix epoch),
        "untracked_files": [str, ...],
        "tracked_stash_ref": str | None,
        "snapshot_dir": str,
        "mode": "copy" | "legacy_stash",
        "status": "ok" | "partial" | "error",
    }
    """
    repo = Path(repo).resolve()
    timestamp = time.time()
    ts_str = time.strftime("%Y%m%d-%H%M%S", time.gmtime(timestamp))
    pid = os.getpid()
    snapshot_id = f"auto-pre-agent-{agent_id}-{ts_str}-{pid}"

    snapshots_root = repo / SNAPSHOTS_DIR_NAME
    snap_dir = snapshots_root / snapshot_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    untracked = _get_untracked_files(repo)
    tracked_stash_ref: Optional[str] = None
    mode = "copy"
    status = "ok"

    # 1. Copy untracked files (they stay in WT — no ghosting)
    copied_untracked: list[str] = []
    if untracked:
        copied_untracked = _copy_untracked(repo, untracked, snap_dir)
        if len(copied_untracked) < len(untracked):
            status = "partial"

    # 2. Stash tracked modifications (no --include-untracked)
    has_tracked = _has_tracked_modifications(repo)
    if has_tracked:
        stash_msg = f"auto-pre-agent-{agent_id}"
        tracked_stash_ref = _stash_tracked(repo, stash_msg)
        if tracked_stash_ref is None and has_tracked:
            status = "partial"

    manifest: dict = {
        "snapshot_id": snapshot_id,
        "agent_id": agent_id,
        "timestamp": timestamp,
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp)),
        "untracked_files": copied_untracked,
        "tracked_stash_ref": tracked_stash_ref,
        "snapshot_dir": str(snap_dir),
        "mode": mode,
        "status": status,
    }

    manifest_path = snap_dir / MANIFEST_FILE
    manifest_path.write_text(json.dumps(manifest, indent=2))

    return manifest


def create_legacy_snapshot(repo: Path, agent_id: str) -> dict:
    """
    Legacy mode (COS_LEGACY_SNAPSHOT=1): stash everything including untracked.
    Untracked files WILL disappear from WT (old behaviour).
    """
    repo = Path(repo).resolve()
    timestamp = time.time()
    ts_str = time.strftime("%Y%m%d-%H%M%S", time.gmtime(timestamp))
    pid = os.getpid()
    snapshot_id = f"cos-{ts_str}-{pid}"

    snapshots_root = repo / SNAPSHOTS_DIR_NAME
    snap_dir = snapshots_root / snapshot_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    stash_msg = f"auto-pre-agent-{agent_id}"
    rc, _, _ = _run(
        [
            "git",
            "stash",
            "push",
            "--include-untracked",
            "--keep-index",
            "-m",
            stash_msg,
            "--",
            ":(exclude).cognitive-os",
            ":(exclude).cognitive-os/**",
            ".",
        ],
        cwd=repo,
    )

    tracked_stash_ref: Optional[str] = None
    status = "ok"
    if rc == 0:
        rc2, out2, _ = _run(["git", "stash", "list", "--max-count=1"], cwd=repo)
        if rc2 == 0 and out2:
            ref = out2.split(":")[0].strip()
            tracked_stash_ref = ref if ref else None
    else:
        status = "error"

    manifest: dict = {
        "snapshot_id": snapshot_id,
        "agent_id": agent_id,
        "timestamp": timestamp,
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp)),
        "untracked_files": [],
        "tracked_stash_ref": tracked_stash_ref,
        "snapshot_dir": str(snap_dir),
        "mode": "legacy_stash",
        "status": status,
    }

    manifest_path = snap_dir / MANIFEST_FILE
    manifest_path.write_text(json.dumps(manifest, indent=2))

    return manifest


def list_snapshots(repo: Path) -> list[dict]:
    """
    Enumerate all snapshots in .cognitive-os/snapshots/.
    Returns list of manifest dicts, sorted by timestamp descending.
    """
    repo = Path(repo).resolve()
    snapshots_root = repo / SNAPSHOTS_DIR_NAME
    if not snapshots_root.is_dir():
        return []

    results: list[dict] = []
    for snap_dir in snapshots_root.iterdir():
        if not snap_dir.is_dir():
            continue
        manifest_path = snap_dir / MANIFEST_FILE
        if not manifest_path.exists():
            continue
        try:
            data = json.loads(manifest_path.read_text())
            results.append(data)
        except Exception:
            continue

    results.sort(key=lambda d: d.get("timestamp", 0), reverse=True)
    return results


def restore_snapshot(
    repo: Path,
    snapshot_id: str,
    files: Optional[list[str]] = None,
) -> dict:
    """
    Restore files from a snapshot.

    - If files is None, restores ALL files captured in the snapshot.
    - For untracked files: copies them back from the snapshot dir to the WT.
    - For tracked files (stash): runs `git stash apply <stash_ref>`.

    Returns a result dict:
    {
        "snapshot_id": str,
        "restored_untracked": [str, ...],
        "restored_tracked": bool,
        "errors": [str, ...],
        "partial": bool,
    }
    """
    repo = Path(repo).resolve()
    snapshots_root = repo / SNAPSHOTS_DIR_NAME
    snap_dir = snapshots_root / snapshot_id
    manifest_path = snap_dir / MANIFEST_FILE

    if not manifest_path.exists():
        return {
            "snapshot_id": snapshot_id,
            "restored_untracked": [],
            "restored_tracked": False,
            "errors": [f"Manifest not found: {manifest_path}"],
            "partial": False,
        }

    manifest = json.loads(manifest_path.read_text())
    errors: list[str] = []
    restored_untracked: list[str] = []
    restored_tracked = False

    # Restore untracked files
    all_untracked = manifest.get("untracked_files", [])
    to_restore_untracked = files if files is not None else all_untracked

    for rel_path in to_restore_untracked:
        if rel_path not in all_untracked:
            errors.append(f"File not in snapshot: {rel_path}")
            continue
        src = snap_dir / rel_path
        dst = repo / rel_path
        if not src.exists():
            errors.append(f"Source missing in snapshot: {rel_path}")
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            restored_untracked.append(rel_path)
        except Exception as exc:
            errors.append(f"Failed to restore {rel_path}: {exc}")

    # Restore tracked files from stash (only when restoring all)
    stash_ref = manifest.get("tracked_stash_ref")
    if stash_ref and files is None:
        rc, _, stderr = _run(
            ["git", "stash", "apply", stash_ref],
            cwd=repo,
        )
        if rc == 0:
            restored_tracked = True
        else:
            errors.append(f"git stash apply {stash_ref} failed: {stderr}")

    # Update manifest to record partial restore
    if files is not None and all_untracked:
        remaining = [f for f in all_untracked if f not in restored_untracked]
        manifest["_partial_restore"] = {
            "restored": restored_untracked,
            "remaining": remaining,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))

    return {
        "snapshot_id": snapshot_id,
        "restored_untracked": restored_untracked,
        "restored_tracked": restored_tracked,
        "errors": errors,
        "partial": files is not None,
    }


def prune_expired(repo: Path, ttl_days: int = DEFAULT_TTL_DAYS) -> list[str]:
    """
    Delete snapshots older than ttl_days. Returns list of deleted snapshot_ids.
    Uses os.path.getmtime (cross-platform) for mtime checks.
    """
    repo = Path(repo).resolve()
    snapshots_root = repo / SNAPSHOTS_DIR_NAME
    if not snapshots_root.is_dir():
        return []

    cutoff = time.time() - (ttl_days * 86400)
    deleted: list[str] = []

    for snap_dir in snapshots_root.iterdir():
        if not snap_dir.is_dir():
            continue
        manifest_path = snap_dir / MANIFEST_FILE
        # Use manifest timestamp if available, else directory mtime
        try:
            mtime = os.path.getmtime(str(snap_dir))
            if manifest_path.exists():
                try:
                    data = json.loads(manifest_path.read_text())
                    mtime = data.get("timestamp", mtime)
                except Exception:
                    pass
            if mtime < cutoff:
                shutil.rmtree(str(snap_dir))
                deleted.append(snap_dir.name)
        except Exception:
            continue

    return deleted
