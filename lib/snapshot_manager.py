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

from lib.stash_sha import resolve_sha_to_ref, resolve_top_stash_sha

# ─── Constants ────────────────────────────────────────────────────────────────

DEFAULT_TTL_DAYS = 30
DEFAULT_MAX_FILE_MB = 50
DEFAULT_MAX_TOTAL_MB = 1024
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
        timeout=30,  # timeout per ADR-278 (default - review)
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
        if not line.startswith("??") and not (line[3:] if len(line) > 2 and line[2] == " " else line[2:].strip()).startswith(".cognitive-os/"):
            return True
    return False


def _tracked_modified_files(repo: Path) -> list[str]:
    """Return tracked/staged paths that would be captured by a pre-agent stash."""
    rc, out, _ = _run(["git", "status", "--porcelain"], cwd=repo)
    if rc != 0 or not out:
        return []
    files: list[str] = []
    for line in out.splitlines():
        if not line or line.startswith("??"):
            continue
        path = line[3:] if len(line) > 2 and line[2] == " " else line[2:].strip()
        # Rename entries look like "old -> new"; stash pathspec should target both
        # endpoints when possible so deleted/renamed state is preserved.
        candidates = [part.strip() for part in path.split(" -> ")]
        for candidate in candidates:
            if candidate and not candidate.startswith(".cognitive-os/") and candidate not in files:
                files.append(candidate)
    return files


def _stash_tracked_files(repo: Path, message: str, files: list[str]) -> tuple[Optional[str], Optional[str]]:
    """Stash the explicit tracked path list and return (ref, sha)."""
    if not files:
        return None, None
    rc, _, _ = _run(["git", "stash", "push", "--keep-index", "-m", message, "--", *files], cwd=repo)
    if rc != 0:
        return None, None
    rc2, out2, _ = _run(["git", "stash", "list", "--max-count=1"], cwd=repo)
    ref = None
    if rc2 == 0 and out2:
        candidate = out2.split(":")[0].strip()
        ref = candidate if candidate else None
    return ref, resolve_top_stash_sha(repo)


def _stash_tracked(repo: Path, message: str) -> tuple[Optional[str], Optional[str]]:
    """
    Run `git stash push --keep-index` (no --include-untracked) to stash
    tracked modifications. Returns (stash_ref_at_capture, stash_sha).

    ``stash_ref_at_capture`` is for forensics only; callers must persist/use
    ``stash_sha`` as the stable identity (ADR-221).
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
        return None, None
    rc2, out2, _ = _run(
        ["git", "stash", "list", "--max-count=1"],
        cwd=repo,
    )
    ref = None
    if rc2 == 0 and out2:
        candidate = out2.split(":")[0].strip()
        ref = candidate if candidate else None
    return ref, resolve_top_stash_sha(repo)


def _copy_worktree_files(
    repo: Path,
    paths: list[str],
    dest: Path,
    *,
    max_file_bytes: Optional[int] = None,
    max_total_bytes: Optional[int] = None,
    missing_reason: str = "missing",
) -> tuple[list[str], list[dict], int]:
    """
    Copy working-tree files to dest/, preserving directory structure.

    Oversized files or files that would exceed the per-snapshot byte budget are
    skipped and reported in the manifest rather than silently filling the disk.
    Returns (copied relative paths, skipped records, copied byte count).
    """
    copied: list[str] = []
    skipped: list[dict] = []
    copied_bytes = 0

    for rel_path in paths:
        src = repo / rel_path
        dst = dest / rel_path
        if not src.exists():
            skipped.append({"path": rel_path, "reason": missing_reason})
            continue
        if not src.is_file():
            skipped.append({"path": rel_path, "reason": "not_regular_file"})
            continue
        try:
            size_bytes = src.stat().st_size
        except OSError as exc:
            skipped.append({"path": rel_path, "reason": f"stat_failed: {exc}"})
            continue

        if max_file_bytes is not None and size_bytes > max_file_bytes:
            skipped.append({
                "path": rel_path,
                "reason": "max_file_bytes",
                "size_bytes": size_bytes,
                "limit_bytes": max_file_bytes,
            })
            continue

        if max_total_bytes is not None and copied_bytes + size_bytes > max_total_bytes:
            skipped.append({
                "path": rel_path,
                "reason": "max_total_bytes",
                "size_bytes": size_bytes,
                "limit_bytes": max_total_bytes,
            })
            continue

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            copied.append(rel_path)
            copied_bytes += size_bytes
        except Exception as exc:
            skipped.append({"path": rel_path, "reason": f"copy_failed: {exc}"})

    return copied, skipped, copied_bytes


def _copy_untracked(
    repo: Path,
    untracked: list[str],
    dest: Path,
    *,
    max_file_bytes: Optional[int] = None,
    max_total_bytes: Optional[int] = None,
) -> tuple[list[str], list[dict], int]:
    """Copy untracked files from the WT to dest/, preserving directory structure."""
    return _copy_worktree_files(
        repo,
        untracked,
        dest,
        max_file_bytes=max_file_bytes,
        max_total_bytes=max_total_bytes,
        missing_reason="missing",
    )


def _copy_tracked_baseline(
    repo: Path,
    tracked: list[str],
    dest: Path,
    *,
    max_file_bytes: Optional[int] = None,
    max_total_bytes: Optional[int] = None,
) -> tuple[list[str], list[dict], int, list[str]]:
    """Copy tracked dirty WT content for no-stash plan restores.

    ADR-222 Phase 1 intentionally does not create a stash. A tracked file that
    is already modified before Agent launch must still round-trip through
    post-agent verification, so the plan snapshot stores the pre-agent
    working-tree bytes beside untracked copies. Deleted tracked paths are
    recorded as deletion baselines.
    """
    existing: list[str] = []
    deleted: list[str] = []
    for rel_path in tracked:
        path = repo / rel_path
        if path.exists():
            existing.append(rel_path)
        else:
            deleted.append(rel_path)
    copied, skipped, copied_bytes = _copy_worktree_files(
        repo,
        existing,
        dest,
        max_file_bytes=max_file_bytes,
        max_total_bytes=max_total_bytes,
        missing_reason="deleted",
    )
    return copied, skipped, copied_bytes, deleted


def _snapshot_size_bytes(snap_dir: Path) -> int:
    """Return the total byte size of regular files below a snapshot directory."""
    total = 0
    for path in snap_dir.rglob("*"):
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:
                continue
    return total


# ─── Public API ───────────────────────────────────────────────────────────────


def plan_snapshot(
    repo: Path,
    agent_id: str,
    *,
    max_file_mb: Optional[int] = DEFAULT_MAX_FILE_MB,
    max_total_mb: Optional[int] = DEFAULT_MAX_TOTAL_MB,
) -> dict:
    """Plan a pre-agent snapshot without mutating git stash state.

    ADR-222 Phase 1: copy untracked files to the snapshot directory and record
    tracked paths that *would* be stashed later. The function intentionally does
    not call ``git stash`` and is safe to run before later launch gates.
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
    tracked_files = _tracked_modified_files(repo)
    max_file_bytes = None if max_file_mb is None else max_file_mb * 1024 * 1024
    max_total_bytes = None if max_total_mb is None else max_total_mb * 1024 * 1024

    copied_untracked: list[str] = []
    skipped_untracked: list[dict] = []
    copied_tracked: list[str] = []
    skipped_tracked: list[dict] = []
    tracked_deleted: list[str] = []
    copied_bytes = 0
    tracked_copied_bytes = 0
    status = "ok"
    if untracked:
        copied_untracked, skipped_untracked, copied_bytes = _copy_untracked(
            repo,
            untracked,
            snap_dir,
            max_file_bytes=max_file_bytes,
            max_total_bytes=max_total_bytes,
        )
        if skipped_untracked or len(copied_untracked) < len(untracked):
            status = "partial"
    if tracked_files:
        remaining_total = None if max_total_bytes is None else max(max_total_bytes - copied_bytes, 0)
        copied_tracked, skipped_tracked, tracked_copied_bytes, tracked_deleted = _copy_tracked_baseline(
            repo,
            tracked_files,
            snap_dir,
            max_file_bytes=max_file_bytes,
            max_total_bytes=remaining_total,
        )
        if skipped_tracked:
            status = "partial"
    if not copied_untracked and not skipped_untracked and not tracked_files:
        status = "skip_clean"

    manifest: dict = {
        "schema_version": "pre-agent-snapshot-plan/v1",
        "snapshot_id": snapshot_id,
        "agent_id": agent_id,
        "timestamp": timestamp,
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp)),
        "untracked_files": copied_untracked,
        "skipped_untracked_files": skipped_untracked,
        "tracked_files": tracked_files,
        "tracked_snapshot_files": copied_tracked,
        "tracked_deleted_files": tracked_deleted,
        "skipped_tracked_files": skipped_tracked,
        "tracked_stash_ref": None,
        "tracked_stash_sha": None,
        "snapshot_dir": str(snap_dir),
        "mode": "copy_plan",
        "status": status,
        "copied_bytes": copied_bytes + tracked_copied_bytes,
        "untracked_copied_bytes": copied_bytes,
        "tracked_copied_bytes": tracked_copied_bytes,
        "retention": {"max_file_mb": max_file_mb, "max_total_mb": max_total_mb},
    }
    (snap_dir / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2))
    return manifest


def commit_snapshot_plan(repo: Path, plan: dict) -> dict:
    """Commit an ADR-222 Phase-1 plan by stashing its tracked path list.

    Refuses malformed plans and only mutates git when tracked files exist. The
    resulting manifest keeps stash SHA as canonical identity per ADR-221.
    """
    repo = Path(repo).resolve()
    if plan.get("schema_version") != "pre-agent-snapshot-plan/v1":
        raise ValueError("expected pre-agent-snapshot-plan/v1")
    agent_id = str(plan.get("agent_id") or "")
    if not agent_id:
        raise ValueError("plan missing agent_id")
    files = [str(path) for path in plan.get("tracked_files") or [] if str(path)]
    stash_ref: Optional[str] = None
    stash_sha: Optional[str] = None
    status = str(plan.get("status") or "ok")
    if files:
        stash_ref, stash_sha = _stash_tracked_files(repo, f"auto-pre-agent-{agent_id}", files)
        if stash_sha:
            status = "stashed"
        else:
            status = "partial"
    elif status == "ok":
        status = "skip_clean"
    committed = dict(plan)
    committed.update({
        "schema_version": "pre-agent-snapshot/v2",
        "tracked_stash_ref": stash_ref,
        "tracked_stash_sha": stash_sha,
        "mode": "copy",
        "status": status,
        "committed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    snapshot_dir = Path(str(committed.get("snapshot_dir") or ""))
    if snapshot_dir:
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        (snapshot_dir / MANIFEST_FILE).write_text(json.dumps(committed, indent=2))
    return committed


def sweep_snapshot_plans(repo: Path, *, ttl_seconds: int = 300) -> list[str]:
    """Delete stale ADR-222 plan files that never committed to stash markers."""
    repo = Path(repo).resolve()
    runtime = repo / ".cognitive-os" / "runtime"
    if not runtime.is_dir():
        return []
    cutoff = time.time() - ttl_seconds
    deleted: list[str] = []
    for plan_path in runtime.glob("pre-agent-plan-*.json"):
        try:
            if plan_path.stat().st_mtime >= cutoff:
                continue
            data = json.loads(plan_path.read_text())
            agent_id = str(data.get("agent_id") or plan_path.stem.replace("pre-agent-plan-", ""))
            marker = runtime / f"pre-agent-snapshot-{agent_id}.json"
            if marker.exists():
                continue
            plan_path.unlink()
            deleted.append(str(plan_path))
        except Exception:
            continue
    return deleted


def create_snapshot(
    repo: Path,
    agent_id: str,
    *,
    max_file_mb: Optional[int] = DEFAULT_MAX_FILE_MB,
    max_total_mb: Optional[int] = DEFAULT_MAX_TOTAL_MB,
) -> dict:
    """
    Create a snapshot of the current working tree before an agent launch.

    Returns a manifest dict:
    {
        "snapshot_id": str,
        "agent_id": str,
        "timestamp": float (unix epoch),
        "untracked_files": [str, ...],
        "tracked_stash_ref": str | None,   # forensics only
        "tracked_stash_sha": str | None,   # canonical identity
        "snapshot_dir": str,
        "mode": "copy" | "legacy_stash",
        "status": "ok" | "partial" | "error",
        "skipped_untracked_files": [{"path": str, "reason": str, ...}],
        "copied_bytes": int,
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
    tracked_stash_sha: Optional[str] = None
    mode = "copy"
    status = "ok"

    max_file_bytes = None if max_file_mb is None else max_file_mb * 1024 * 1024
    max_total_bytes = None if max_total_mb is None else max_total_mb * 1024 * 1024

    # 1. Copy untracked files (they stay in WT — no ghosting)
    copied_untracked: list[str] = []
    skipped_untracked: list[dict] = []
    copied_bytes = 0
    if untracked:
        copied_untracked, skipped_untracked, copied_bytes = _copy_untracked(
            repo,
            untracked,
            snap_dir,
            max_file_bytes=max_file_bytes,
            max_total_bytes=max_total_bytes,
        )
        if skipped_untracked or len(copied_untracked) < len(untracked):
            status = "partial"

    # 2. Stash tracked modifications (no --include-untracked)
    has_tracked = _has_tracked_modifications(repo)
    if has_tracked:
        stash_msg = f"auto-pre-agent-{agent_id}"
        tracked_stash_ref, tracked_stash_sha = _stash_tracked(repo, stash_msg)
        if tracked_stash_sha is None and has_tracked:
            status = "partial"

    manifest: dict = {
        "snapshot_id": snapshot_id,
        "agent_id": agent_id,
        "timestamp": timestamp,
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp)),
        "untracked_files": copied_untracked,
        "skipped_untracked_files": skipped_untracked,
        "copied_bytes": copied_bytes,
        "retention": {
            "max_file_mb": max_file_mb,
            "max_total_mb": max_total_mb,
        },
        "tracked_stash_ref": tracked_stash_ref,
        "tracked_stash_sha": tracked_stash_sha,
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
    tracked_stash_sha: Optional[str] = None
    status = "ok"
    if rc == 0:
        rc2, out2, _ = _run(["git", "stash", "list", "--max-count=1"], cwd=repo)
        if rc2 == 0 and out2:
            ref = out2.split(":")[0].strip()
            tracked_stash_ref = ref if ref else None
        tracked_stash_sha = resolve_top_stash_sha(repo)
    else:
        status = "error"

    manifest: dict = {
        "snapshot_id": snapshot_id,
        "agent_id": agent_id,
        "timestamp": timestamp,
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp)),
        "untracked_files": [],
        "tracked_stash_ref": tracked_stash_ref,
        "tracked_stash_sha": tracked_stash_sha,
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
    - For tracked files (stash): runs `git stash apply <stash_sha>` when available.

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
    restored_tracked_files: list[str] = []
    restored_tracked = False

    # Restore file copies captured in the snapshot directory.
    all_untracked = manifest.get("untracked_files", [])
    all_tracked_copies = manifest.get("tracked_snapshot_files", [])
    all_tracked_deleted = manifest.get("tracked_deleted_files", [])
    requested = files if files is not None else [*all_untracked, *all_tracked_copies, *all_tracked_deleted]

    for rel_path in requested:
        is_untracked = rel_path in all_untracked
        is_tracked_copy = rel_path in all_tracked_copies
        is_tracked_deleted = rel_path in all_tracked_deleted
        if not is_untracked and not is_tracked_copy and not is_tracked_deleted:
            errors.append(f"File not in snapshot: {rel_path}")
            continue
        if is_tracked_deleted:
            dst = repo / rel_path
            try:
                if dst.is_dir():
                    shutil.rmtree(str(dst))
                elif dst.exists():
                    dst.unlink()
                restored_tracked_files.append(rel_path)
            except Exception as exc:
                errors.append(f"Failed to restore deleted baseline {rel_path}: {exc}")
            continue
        src = snap_dir / rel_path
        dst = repo / rel_path
        if not src.exists():
            errors.append(f"Source missing in snapshot: {rel_path}")
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            if is_untracked:
                restored_untracked.append(rel_path)
            else:
                restored_tracked_files.append(rel_path)
        except Exception as exc:
            errors.append(f"Failed to restore {rel_path}: {exc}")

    # Restore tracked files from stash (only when restoring all)
    stash_sha = manifest.get("tracked_stash_sha")
    stash_ref = manifest.get("tracked_stash_ref")
    stash_identity = stash_sha or stash_ref
    if stash_identity and files is None:
        if stash_sha and not resolve_sha_to_ref(repo, stash_sha):
            rc, stderr = 1, "stash SHA not present in stash list"
        else:
            rc, _, stderr = _run(
                ["git", "stash", "apply", stash_identity],
                cwd=repo,
            )
        if rc == 0:
            restored_tracked = True
        else:
            errors.append(f"git stash apply {stash_identity} failed: {stderr}")

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
        "restored_tracked_files": restored_tracked_files,
        "errors": errors,
        "partial": files is not None,
    }


def prune_expired(
    repo: Path,
    ttl_days: int = DEFAULT_TTL_DAYS,
    *,
    max_total_mb: Optional[int] = None,
) -> list[str]:
    """
    Delete snapshots older than ttl_days and optionally enforce a repo byte cap.

    When max_total_mb is provided, snapshots are pruned oldest-first after TTL
    pruning until the aggregate snapshot directory size is at or below the cap.
    Returns list of deleted snapshot_ids.
    """
    repo = Path(repo).resolve()
    snapshots_root = repo / SNAPSHOTS_DIR_NAME
    if not snapshots_root.is_dir():
        return []

    cutoff = time.time() - (ttl_days * 86400)
    deleted: list[str] = []

    def snapshot_timestamp(snap_dir: Path) -> float:
        manifest_path = snap_dir / MANIFEST_FILE
        mtime = os.path.getmtime(str(snap_dir))
        if manifest_path.exists():
            try:
                data = json.loads(manifest_path.read_text())
                return float(data.get("timestamp", mtime))
            except Exception:
                return mtime
        return mtime

    for snap_dir in snapshots_root.iterdir():
        if not snap_dir.is_dir():
            continue
        try:
            if snapshot_timestamp(snap_dir) < cutoff:
                shutil.rmtree(str(snap_dir))
                deleted.append(snap_dir.name)
        except Exception:
            continue

    if max_total_mb is None:
        return deleted

    max_total_bytes = max_total_mb * 1024 * 1024
    remaining_dirs = [p for p in snapshots_root.iterdir() if p.is_dir()]
    sized = [(p, snapshot_timestamp(p), _snapshot_size_bytes(p)) for p in remaining_dirs]
    total_bytes = sum(size for _, _, size in sized)

    for snap_dir, _, size_bytes in sorted(sized, key=lambda item: item[1]):
        if total_bytes <= max_total_bytes:
            break
        try:
            shutil.rmtree(str(snap_dir))
            deleted.append(snap_dir.name)
            total_bytes -= size_bytes
        except Exception:
            continue

    return deleted
