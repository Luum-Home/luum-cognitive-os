from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = PROJECT_ROOT / "hooks" / "agent-prelaunch.sh"


def _init_repo(path: Path, branch: str = "main") -> None:
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=path, check=True)
    (path / "README.md").write_text("test\n")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=path, check=True)


def _run_prelaunch(project: Path, payload: dict, *, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        "COGNITIVE_OS_PROJECT_DIR": str(project),
        "COGNITIVE_OS_SESSION_ID": "s1",
        "COS_SKIP_GOVERNED_INVENTORY": "1",
        "COS_SKIP_WORKTREE_DIVERGENCE_AUDIT": "1",
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )


@pytest.mark.behavior
def test_branch_per_task_prelaunch_blocks_write_agent_on_wrong_branch(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _init_repo(project, "main")

    result = _run_prelaunch(
        project,
        {
            "tool_name": "Agent",
            "tool_use_id": "toolu_123",
            "tool_input": {
                "task_id": "implement-docs-branch-task",
                "description": "Implement docs branch task",
                "lifecycle_mode": "write",
                "subagent_type": "general-purpose",
            },
        },
    )

    assert result.returncode == 2
    assert "ADR-225 BRANCH-PER-TASK PREFLIGHT BLOCK" in result.stderr
    assert "codex/task" in result.stderr


@pytest.mark.behavior
def test_branch_per_task_prelaunch_allows_canonical_branch(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _init_repo(project, "codex/task/implement-docs-branch-task")

    result = _run_prelaunch(
        project,
        {
            "tool_name": "Agent",
            "tool_use_id": "toolu_123",
            "tool_input": {
                "task_id": "implement-docs-branch-task",
                "description": "Implement docs branch task",
                "lifecycle_mode": "write",
                "subagent_type": "general-purpose",
            },
        },
    )

    assert result.returncode == 0
