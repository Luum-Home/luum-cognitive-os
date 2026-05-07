# SCOPE: both
"""ADR-223 write-agent lifecycle helpers."""
from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class AgentWorktree:
    schema_version: str
    task_id: str
    session_id: str
    branch: str
    worktree_path: str
    source_head: str
    created: bool
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class AgentLifecycleError(RuntimeError):
    """Raised when an ADR-223 lifecycle operation fails."""


def _run_git(project: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(project), capture_output=True, text=True, timeout=20)


def slugify(value: str, *, default: str = "agent") -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip(".-_").lower()
    return (slug or default)[:80]


def _repo_name(project: Path) -> str:
    return slugify(project.resolve().name, default="repo")


def default_worktree_root(project: Path) -> Path:
    override = os.environ.get("COS_AGENT_WORKTREE_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return project.resolve().parent / ".cos-agent-worktrees" / _repo_name(project)


def _head_sha(project: Path) -> str:
    proc = _run_git(project, ["rev-parse", "HEAD"])
    if proc.returncode != 0:
        raise AgentLifecycleError(proc.stderr.strip() or "git rev-parse HEAD failed")
    return proc.stdout.strip()


def _branch_exists(project: Path, branch: str) -> bool:
    proc = _run_git(project, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"])
    return proc.returncode == 0


def _unique_branch(project: Path, base: str) -> str:
    if not _branch_exists(project, base):
        return base
    for idx in range(2, 100):
        candidate = f"{base}-{idx}"
        if not _branch_exists(project, candidate):
            return candidate
    raise AgentLifecycleError(f"could not allocate branch for {base}")


@contextmanager
def _worktree_add_lock(project: Path) -> Iterator[None]:
    runtime = project / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    lock_path = runtime / "agent-worktree-add.lock"
    with lock_path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def prepare_agent_worktree(
    project_dir: str | Path,
    *,
    task_id: str,
    session_id: str,
    worktree_root: str | Path | None = None,
) -> AgentWorktree:
    """Create or reuse a dedicated worktree for a write-capable agent."""
    project = Path(project_dir).resolve()
    if _run_git(project, ["rev-parse", "--is-inside-work-tree"]).returncode != 0:
        raise AgentLifecycleError(f"not a git worktree: {project}")

    task_slug = slugify(task_id)
    root = Path(worktree_root).resolve() if worktree_root else default_worktree_root(project)
    target = root / task_slug
    manifest_dir = project / ".cognitive-os" / "runtime" / "agent-worktrees"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{task_slug}.json"
    head = _head_sha(project)

    with _worktree_add_lock(project):
        created = False
        branch = f"codex/agent/{task_slug}"
        if target.exists():
            branch_proc = _run_git(target, ["branch", "--show-current"])
            branch = branch_proc.stdout.strip() or branch
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            branch = _unique_branch(project, branch)
            proc = _run_git(project, ["worktree", "add", str(target), "-b", branch, head])
            if proc.returncode != 0:
                raise AgentLifecycleError(proc.stderr.strip() or "git worktree add failed")
            created = True

        record = AgentWorktree(
            schema_version="agent-lifecycle-worktree/v1",
            task_id=task_id,
            session_id=session_id,
            branch=branch,
            worktree_path=str(target),
            source_head=head,
            created=created,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        manifest_path.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return record
