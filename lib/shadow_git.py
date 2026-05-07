# SCOPE: both
"""ADR-227 shadow-git checkpoint substrate."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


class ShadowGitError(RuntimeError):
    """Base error for shadow-git operations."""


class RestorePreviewRequired(ShadowGitError):
    """Raised when restore is attempted without preview/confirmation."""


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


def restore_files(workspace: str | Path, session_id: str, tree_sha: str, *, preview_path: str | Path | None = None, yes: bool = False) -> None:
    if not yes or not preview_path or not Path(preview_path).is_file():
        raise RestorePreviewRequired("restore requires preview_path and yes=True")
    root = Path(workspace).resolve()
    repo = init_session_repo(root, session_id)
    entries = _tree_entries(repo, tree_sha)
    current = set(_list_files(root))
    target = {Path(path) for path in entries}
    for rel in current - target:
        (root / rel).unlink(missing_ok=True)
    for rel_str, blob in entries.items():
        rel = Path(rel_str)
        data = _run(["git", f"--git-dir={repo}", "cat-file", "-p", blob])
        if data.returncode != 0:
            raise ShadowGitError(data.stderr.strip() or f"cat-file failed for {rel_str}")
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data.stdout.encode("utf-8"))


def restore(workspace: str | Path, session_id: str, tree_sha: str, *, mode: Literal["files_only"] = "files_only", preview_path: str | Path | None = None, yes: bool = False) -> None:
    if mode != "files_only":
        raise ShadowGitError("Slice A supports files_only restore; conversation modes are deferred")
    restore_files(workspace, session_id, tree_sha, preview_path=preview_path, yes=yes)


def prune_session_repo(workspace: str | Path, session_id: str) -> None:
    path = shadow_repo_path(workspace, session_id).parent
    if path.exists():
        shutil.rmtree(path)
