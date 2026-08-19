"""ADR-245 chaos-lane read-only guard for production source.

Chaos tests may break runtime conditions, but they must not mutate the checked-out
production source under lib/, scripts/, or hooks/. The autouse fixture snapshots
those surfaces before each chaos test, restores any mutation at teardown, and
fails the test with a file-named diagnostic.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest


PROTECTED_DIRS = ("cos_lib", "lib", "scripts", "hooks")
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


def _uncommitted_protected_paths(root: Path) -> list[str]:
    """Paths under the protected dirs that carry uncommitted work right now."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all", "--", *PROTECTED_DIRS],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []          # not a git checkout, or git unavailable: nothing to assert against
    if proc.returncode != 0:
        return []
    return [line[3:].strip() for line in proc.stdout.splitlines() if line.strip()]


@pytest.fixture(scope="session", autouse=True)
def chaos_requires_clean_protected_tree():
    """Refuse to run the chaos lane over uncommitted work in the protected dirs.

    The restore below cannot tell WHO changed a file: it compares bytes against a
    snapshot and rewrites anything that differs. Under one process that is exactly
    right -- the only writer is the test. Under concurrency it is exactly wrong,
    and it destroys the other writer's work silently, because the file comes back
    byte-identical to HEAD and `git status` on it is empty afterwards.

    Measured 2026-08-19: three separate uncommitted edits to
    scripts/detect_runner_capacity.py and scripts/pytest-with-summary.sh vanished
    while chaos tests ran in another process. The teardown named the file in its
    own failure message and nobody was reading that output -- the work simply was
    not there any more. A fourth loss missed the runner patches by 35 seconds.

    The irony is the point: ADR-245 exists BECAUSE of concurrency. Its context
    records "a concurrent agent reading the same checkout observed an inconsistent
    module body". The guard written to protect concurrent agents was eating their
    work.

    This precondition does not weaken ADR-245 -- snapshot-and-revert stays exactly
    as decided. It makes the decision's own assumption true by construction: with
    the protected dirs clean at session start, anything dirty at teardown WAS the
    test. Committing or stashing first costs seconds; the alternative costs work
    that leaves no trace.

    CI is unaffected: a fresh checkout has nothing uncommitted. Escape hatch for a
    deliberate local run: COS_ALLOW_CHAOS_DIRTY_TREE=1.
    """
    if os.environ.get("COS_ALLOW_CHAOS_DIRTY_TREE") == "1":
        yield
        return

    dirty = _uncommitted_protected_paths(_repo_root())
    if dirty:
        shown = "\n  ".join(dirty[:20])
        more = f"\n  ... and {len(dirty) - 20} more" if len(dirty) > 20 else ""
        pytest.fail(
            "ADR-245: the chaos lane restores every file under "
            f"{', '.join(PROTECTED_DIRS)} to its pre-test bytes, and cannot tell "
            "your uncommitted work from a test's mutation. It would be reverted "
            "silently, with no trace left in git status.\n\n"
            f"Uncommitted right now:\n  {shown}{more}\n\n"
            "Commit or stash these first. To run anyway, accepting that they may "
            "be reverted: COS_ALLOW_CHAOS_DIRTY_TREE=1",
            pytrace=False,
        )
    yield


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
