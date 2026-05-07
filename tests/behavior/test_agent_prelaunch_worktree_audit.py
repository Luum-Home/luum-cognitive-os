"""Behavior tests for ADR-220 worktree divergence gating in Agent prelaunch."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "hooks" / "agent-prelaunch.sh"


def _run(cmd: list[str], cwd: Path, *, input_text: str | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(cmd, cwd=cwd, input=input_text, text=True, capture_output=True, env=merged, timeout=30)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = _run(["git", *args], repo)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


def _init_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "hooks").symlink_to(ROOT / "hooks", target_is_directory=True)
    (project / "scripts").symlink_to(ROOT / "scripts", target_is_directory=True)
    (project / "lib").symlink_to(ROOT / "lib", target_is_directory=True)
    (project / ".gitignore").write_text(".cognitive-os/\nhooks\nscripts\nlib\n", encoding="utf-8")
    _git(project, "init", "-b", "main")
    _git(project, "config", "user.email", "test@example.invalid")
    _git(project, "config", "user.name", "Test User")
    (project / "app.txt").write_text("base\n", encoding="utf-8")
    _git(project, "add", ".gitignore", "app.txt")
    _git(project, "commit", "-m", "base")
    return project


def _payload() -> str:
    return json.dumps(
        {
            "tool_name": "Agent",
            "tool_use_id": "toolu_adr220",
            "tool_input": {
                "subagent_type": "general-purpose",
                "description": "write-capable launch should be blocked by worktree conflict",
            },
        }
    )


def test_agent_prelaunch_blocks_worktree_dirty_path_overlap(tmp_path: Path) -> None:
    project = _init_project(tmp_path)
    _git(project, "checkout", "-b", "agent-work")
    worktree = tmp_path / "agent-worktree"
    _git(project, "checkout", "main")
    _git(project, "worktree", "add", str(worktree), "agent-work")

    (worktree / "app.txt").write_text("agent WIP\n", encoding="utf-8")
    (project / "app.txt").write_text("main fix\n", encoding="utf-8")
    _git(project, "add", "app.txt")
    _git(project, "commit", "-m", "main fix")

    result = _run(
        ["bash", str(HOOK)],
        project,
        input_text=_payload(),
        env={
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "CLAUDE_PROJECT_DIR": str(project),
            "COGNITIVE_OS_SESSION_ID": "adr220-test-session",
            "COS_SKIP_GOVERNED_INVENTORY": "1",
        },
    )

    assert result.returncode == 2
    assert "ADR-220 WORKTREE PREFLIGHT BLOCK" in result.stderr
    assert "path-conflict-pending" in result.stderr
    assert "app.txt" in result.stderr

