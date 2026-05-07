# SCOPE: both
"""ADR-225 branch-per-task policy helpers."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from lib.agent_lifecycle import slugify

SCHEMA_VERSION = "branch-per-task/v1"
DEFAULT_PREFIX = "codex/task"


class BranchTaskPolicyError(RuntimeError):
    """Raised when branch-per-task policy cannot be evaluated."""


@dataclass(frozen=True)
class BranchTaskVerdict:
    schema_version: str
    status: str
    expected_branch: str
    current_branch: str
    task_id: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "expected_branch": self.expected_branch,
            "current_branch": self.current_branch,
            "task_id": self.task_id,
            "detail": self.detail,
        }


def branch_for_task(task_id: str, *, prefix: str = DEFAULT_PREFIX) -> str:
    """Return the canonical branch name for a task id."""
    return f"{prefix.rstrip('/')}/{slugify(task_id, default='task')}"


def current_branch(project_dir: str | Path) -> str:
    proc = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=str(Path(project_dir).resolve()),
        capture_output=True,
        text=True,
        timeout=5,
    )
    if proc.returncode != 0:
        raise BranchTaskPolicyError(proc.stderr.strip() or "git branch --show-current failed")
    return proc.stdout.strip()


def evaluate_branch_for_task(
    project_dir: str | Path,
    *,
    task_id: str,
    prefix: str = DEFAULT_PREFIX,
    current: str | None = None,
) -> BranchTaskVerdict:
    """Evaluate whether the current branch matches ADR-225 task policy."""
    expected = branch_for_task(task_id, prefix=prefix)
    actual = current if current is not None else current_branch(project_dir)
    if actual == expected:
        return BranchTaskVerdict(SCHEMA_VERSION, "PASS", expected, actual, task_id, "branch matches task")
    return BranchTaskVerdict(
        SCHEMA_VERSION,
        "BLOCK",
        expected,
        actual,
        task_id,
        "write/cloud task must run on its canonical branch-per-task branch",
    )
