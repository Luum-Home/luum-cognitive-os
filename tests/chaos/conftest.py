"""ADR-245 chaos-lane read-only guard for production source.

Chaos tests may break runtime conditions, but they must not mutate the checked-out
production source under lib/, scripts/, or hooks/. The autouse fixture snapshots
those surfaces before each chaos test, restores any mutation at teardown, and
fails the test with a file-named diagnostic.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytest


PROTECTED_DIRS = ("lib", "scripts", "hooks")
IGNORED_PARTS = {"__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class SourceSnapshot:
    digest: str
    size: int
    bytes_value: bytes


@dataclass(frozen=True)
class SourceMutation:
    kind: str
    path: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ignored(path: Path) -> bool:
    return bool(IGNORED_PARTS.intersection(path.parts)) or path.suffix in IGNORED_SUFFIXES


def _protected_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirname in PROTECTED_DIRS:
        base = root / dirname
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and not _ignored(path):
                files.append(path)
    return files


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def take_source_snapshot(root: Path) -> dict[Path, SourceSnapshot]:
    snapshot: dict[Path, SourceSnapshot] = {}
    for path in _protected_files(root):
        data = path.read_bytes()
        snapshot[path.relative_to(root)] = SourceSnapshot(digest=_digest(data), size=len(data), bytes_value=data)
    return snapshot


def restore_source_mutations(root: Path, snapshot: dict[Path, SourceSnapshot]) -> list[SourceMutation]:
    mutations: list[SourceMutation] = []
    seen = set(snapshot)
    for rel_path, before in snapshot.items():
        path = root / rel_path
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(before.bytes_value)
            mutations.append(SourceMutation("deleted-restored", rel_path.as_posix()))
            continue
        data = path.read_bytes()
        if len(data) != before.size or _digest(data) != before.digest:
            path.write_bytes(before.bytes_value)
            mutations.append(SourceMutation("modified-restored", rel_path.as_posix()))
    for path in _protected_files(root):
        rel_path = path.relative_to(root)
        if rel_path in seen:
            continue
        path.unlink()
        mutations.append(SourceMutation("added-removed", rel_path.as_posix()))
    return mutations


@pytest.fixture(autouse=True)
def chaos_readonly_workspace():
    root = _repo_root()
    snapshot = take_source_snapshot(root)
    yield
    mutations = restore_source_mutations(root, snapshot)
    if mutations:
        sample = ", ".join(f"{m.kind}:{m.path}" for m in mutations[:20])
        pytest.fail(
            "ADR-245 chaos_readonly_workspace restored production-source mutation(s): "
            f"{sample}. Chaos tests must use fixture copies or dependency injection, "
            "not writes to lib/, scripts/, or hooks/.",
            pytrace=False,
        )
