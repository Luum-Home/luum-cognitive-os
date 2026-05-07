# SCOPE: both
"""ADR-227 shadow-git checkpoint substrate."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from lib.session_bus import append_session_event, event_index_path, session_counter_path, session_stream_path, truncate_session_events


class ShadowGitError(RuntimeError):
    """Base error for shadow-git operations."""


class RestorePreviewRequired(ShadowGitError):
    """Raised when restore is attempted without preview/confirmation."""


class ConversationRestoreRequired(ShadowGitError):
    """Raised when conversation restore lacks target seq/confirmation."""


@dataclass(frozen=True)
class ShadowSnapshot:
    schema_version: str
    project_id: str
    session_id: str
    tree_sha: str
    shadow_repo: str
    manifest_path: str
    created_at: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, capture_output=True, text=True, timeout=30)


def project_id(workspace: str | Path) -> str:
    root = Path(workspace).resolve()
    raw = str(root)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def shadow_base_dir() -> Path:
    override = os.environ.get("COS_SHADOW_GIT_BASE")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".cognitive-os" / "snapshots"


def shadow_repo_path(workspace: str | Path, session_id: str) -> Path:
    return shadow_base_dir() / project_id(workspace) / session_id / ".git"


def init_session_repo(workspace: str | Path, session_id: str) -> Path:
    repo = shadow_repo_path(workspace, session_id)
    if not repo.exists():
        repo.parent.mkdir(parents=True, exist_ok=True)
        proc = _run(["git", "init", "--bare", str(repo)])
        if proc.returncode != 0:
            raise ShadowGitError(proc.stderr.strip() or "git init --bare failed")
    return repo


def _list_files(workspace: Path) -> list[Path]:
    files: list[Path] = []
    for path in workspace.rglob("*"):
        rel = path.relative_to(workspace)
        parts = set(rel.parts)
        if ".git" in parts or ".cognitive-os" in parts or "node_modules" in parts or "__pycache__" in parts:
            continue
        if path.is_file():
            files.append(rel)
    return sorted(files)


def _build_index(repo: Path, workspace: Path, files: list[Path]) -> Path:
    index = repo.parent / "shadow.index"
    index.unlink(missing_ok=True)
    env = {**os.environ, "GIT_DIR": str(repo), "GIT_INDEX_FILE": str(index)}
    for rel in files:
        full = workspace / rel
        blob = _run(["git", "hash-object", "-w", str(full)], env=env)
        if blob.returncode != 0:
            raise ShadowGitError(blob.stderr.strip() or f"hash-object failed for {rel}")
        add = _run(["git", "update-index", "--add", "--cacheinfo", "100644", blob.stdout.strip(), str(rel)], env=env)
        if add.returncode != 0:
            raise ShadowGitError(add.stderr.strip() or f"update-index failed for {rel}")
    return index


def snapshot(workspace: str | Path, session_id: str) -> ShadowSnapshot:
    root = Path(workspace).resolve()
    repo = init_session_repo(root, session_id)
    files = _list_files(root)
    index = _build_index(repo, root, files)
    env = {**os.environ, "GIT_DIR": str(repo), "GIT_INDEX_FILE": str(index)}
    tree = _run(["git", "write-tree"], env=env)
    if tree.returncode != 0:
        raise ShadowGitError(tree.stderr.strip() or "git write-tree failed")
    tree_sha = tree.stdout.strip()
    manifest_dir = root / ".cognitive-os" / "shadow-git"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{session_id}-{tree_sha}.json"
    record = ShadowSnapshot(
        schema_version="shadow-git/v1",
        project_id=project_id(root),
        session_id=session_id,
        tree_sha=tree_sha,
        shadow_repo=str(repo),
        manifest_path=str(manifest_path),
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    manifest_path.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def _tree_entries(repo: Path, tree_sha: str) -> dict[str, str]:
    proc = _run(["git", f"--git-dir={repo}", "ls-tree", "-r", tree_sha])
    if proc.returncode != 0:
        raise ShadowGitError(proc.stderr.strip() or "git ls-tree failed")
    entries: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        meta, _, path = line.partition("\t")
        if not path:
            continue
        sha = meta.split()[2]
        entries[path] = sha
    return entries


def preview(workspace: str | Path, session_id: str, tree_sha: str) -> Path:
    root = Path(workspace).resolve()
    repo = init_session_repo(root, session_id)
    target = _tree_entries(repo, tree_sha)
    current_files = {str(rel) for rel in _list_files(root)}
    target_files = set(target)
    lines: list[str] = []
    for path in sorted(target_files - current_files):
        lines.append(f"A\t{path}")
    for path in sorted(current_files - target_files):
        lines.append(f"D\t{path}")
    for path in sorted(current_files & target_files):
        current_blob = _run(["git", "hash-object", str(root / path)])
        if current_blob.returncode == 0 and current_blob.stdout.strip() != target[path]:
            lines.append(f"M\t{path}")
    reports = root / ".cognitive-os" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    out = reports / f"restore-preview-{int(time.time())}-{tree_sha[:8]}.txt"
    out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return out


def _restore_lock_path(workspace: Path, session_id: str) -> Path:
    return workspace / ".cognitive-os" / "sessions" / f"{session_id}.restore.lock"


@contextmanager
def _restore_locked(workspace: Path, session_id: str):
    path = _restore_lock_path(workspace, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read_event_store_bytes(workspace: Path, session_id: str) -> tuple[Path, bytes | None, Path, bytes | None, Path, bytes | None]:
    stream = session_stream_path(workspace, session_id)
    counter = session_counter_path(workspace, session_id)
    index = event_index_path(workspace)
    return (
        stream,
        stream.read_bytes() if stream.exists() else None,
        counter,
        counter.read_bytes() if counter.exists() else None,
        index,
        index.read_bytes() if index.exists() else None,
    )


def _restore_event_store_bytes(
    stream: Path,
    stream_bytes: bytes | None,
    counter: Path,
    counter_bytes: bytes | None,
    index: Path,
    index_bytes: bytes | None,
) -> None:
    stream.parent.mkdir(parents=True, exist_ok=True)
    if stream_bytes is None:
        stream.unlink(missing_ok=True)
    else:
        stream.write_bytes(stream_bytes)
    counter.parent.mkdir(parents=True, exist_ok=True)
    if counter_bytes is None:
        counter.unlink(missing_ok=True)
    else:
        counter.write_bytes(counter_bytes)
    index.parent.mkdir(parents=True, exist_ok=True)
    if index_bytes is None:
        index.unlink(missing_ok=True)
    else:
        index.write_bytes(index_bytes)


def _restore_files_unchecked(workspace: Path, session_id: str, tree_sha: str) -> None:
    repo = init_session_repo(workspace, session_id)
    entries = _tree_entries(repo, tree_sha)
    current = set(_list_files(workspace))
    target = {Path(path) for path in entries}
    for rel in current - target:
        (workspace / rel).unlink(missing_ok=True)
    for rel_str, blob in entries.items():
        rel = Path(rel_str)
        data = _run(["git", f"--git-dir={repo}", "cat-file", "-p", blob])
        if data.returncode != 0:
            raise ShadowGitError(data.stderr.strip() or f"cat-file failed for {rel_str}")
        dest = workspace / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data.stdout.encode("utf-8"))


def truncate_conversation(workspace: str | Path, session_id: str, target_seq: int) -> dict[str, Any]:
    if target_seq < 0:
        raise ConversationRestoreRequired("target_seq must be >= 0")
    return truncate_session_events(session_id, project_dir=workspace, target_seq=target_seq, strict_durability=True)


def snapshot_event(
    workspace: str | Path,
    session_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append an ADR-226 event envelope carrying the current shadow tree SHA."""
    snap = snapshot(workspace, session_id)
    enriched = {**(payload or {}), "file_tree_sha": snap.tree_sha, "shadow_manifest_path": snap.manifest_path}
    return append_session_event(
        event_type,
        enriched,
        project_dir=workspace,
        session_id=session_id,
        strict_durability=True,
    )


def restore_files(workspace: str | Path, session_id: str, tree_sha: str, *, preview_path: str | Path | None = None, yes: bool = False) -> None:
    if not yes or not preview_path or not Path(preview_path).is_file():
        raise RestorePreviewRequired("restore requires preview_path and yes=True")
    _restore_files_unchecked(Path(workspace).resolve(), session_id, tree_sha)


def restore(
    workspace: str | Path,
    session_id: str,
    tree_sha: str,
    *,
    mode: Literal["files_only", "conversation_only", "files_and_conversation"] = "files_only",
    preview_path: str | Path | None = None,
    yes: bool = False,
    target_seq: int | None = None,
) -> dict[str, Any]:
    """Restore a shadow checkpoint.

    ``files_and_conversation`` is guarded by a project-local restore lock and a
    rollback safety snapshot: if file restore or conversation truncation fails,
    the previous files and event stream bytes are restored before the exception
    is re-raised.
    """
    root = Path(workspace).resolve()
    if mode == "files_only":
        restore_files(root, session_id, tree_sha, preview_path=preview_path, yes=yes)
        return {"mode": mode, "tree_sha": tree_sha}
    if target_seq is None:
        raise ConversationRestoreRequired("conversation restore requires target_seq")
    if not yes:
        raise ConversationRestoreRequired("conversation restore requires yes=True")
    if mode == "conversation_only":
        with _restore_locked(root, session_id):
            result = truncate_conversation(root, session_id, target_seq)
            event = append_session_event(
                "shadow-git-restore",
                {"mode": mode, "target_seq": target_seq, "file_tree_sha": tree_sha},
                project_dir=root,
                session_id=session_id,
                strict_durability=True,
            )
        return {"mode": mode, "tree_sha": tree_sha, "target_seq": target_seq, "truncate": result, "event_seq": event["seq"]}
    if mode != "files_and_conversation":
        raise ShadowGitError(f"unsupported restore mode: {mode}")
    if not preview_path or not Path(preview_path).is_file():
        raise RestorePreviewRequired("files_and_conversation restore requires preview_path and yes=True")
    with _restore_locked(root, session_id):
        safety = snapshot(root, f"{session_id}-pre-restore-{int(time.time())}")
        stream, stream_bytes, counter, counter_bytes, index, index_bytes = _read_event_store_bytes(root, session_id)
        try:
            _restore_files_unchecked(root, session_id, tree_sha)
            result = truncate_conversation(root, session_id, target_seq)
            event = append_session_event(
                "shadow-git-restore",
                {
                    "mode": mode,
                    "target_seq": target_seq,
                    "file_tree_sha": tree_sha,
                    "safety_tree_sha": safety.tree_sha,
                },
                project_dir=root,
                session_id=session_id,
                strict_durability=True,
            )
        except Exception:
            _restore_files_unchecked(root, safety.session_id, safety.tree_sha)
            _restore_event_store_bytes(stream, stream_bytes, counter, counter_bytes, index, index_bytes)
            raise
    return {"mode": mode, "tree_sha": tree_sha, "target_seq": target_seq, "truncate": result, "event_seq": event["seq"]}


def prune_session_repo(workspace: str | Path, session_id: str) -> None:
    path = shadow_repo_path(workspace, session_id).parent
    if path.exists():
        shutil.rmtree(path)
