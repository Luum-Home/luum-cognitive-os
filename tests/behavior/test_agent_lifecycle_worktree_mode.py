from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


@pytest.mark.behavior
def test_agent_prelaunch_worktree_mode_prepares_context_without_stash(project_root: Path, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "scripts").mkdir()
    (repo / "scripts" / "cos-agent-worktree-prepare").symlink_to(project_root / "scripts" / "cos-agent-worktree-prepare")

    payload = {"tool_name": "Agent", "tool_use_id": "toolu_worktree", "tool_input": {"prompt": "Write README update"}}
    env = {
        "CLAUDE_PROJECT_DIR": str(repo),
        "COGNITIVE_OS_PROJECT_DIR": str(repo),
        "COGNITIVE_OS_SESSION_ID": "s1",
        "COS_AGENT_LIFECYCLE_MODE": "worktree",
        "COS_AGENT_WORKTREE_ROOT": str(tmp_path / "agent-worktrees"),
        "COS_SKIP_GOVERNED_INVENTORY": "1",
        "COS_SKIP_WORKTREE_DIVERGENCE_AUDIT": "1",
    }
    result = subprocess.run(
        ["bash", str(project_root / "hooks" / "agent-prelaunch.sh")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={**env},
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    context = out["hookSpecificOutput"]["additionalContext"]
    assert "ADR-223" in context
    assert "WORKING DIR:" in context
    marker = repo / ".cognitive-os" / "runtime" / "suppress-agent-snapshot-toolu_worktree.json"
    assert marker.is_file()
    assert subprocess.run(["git", "-C", str(repo), "stash", "list"], capture_output=True, text=True).stdout == ""


@pytest.mark.behavior
def test_pre_agent_snapshot_suppressed_for_agent_worktree_marker(project_root: Path, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("dirty\n", encoding="utf-8")
    runtime = repo / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "suppress-agent-snapshot-toolu_worktree.json").write_text("{}\n", encoding="utf-8")

    payload = {"tool_name": "Agent", "tool_use_id": "toolu_worktree", "tool_input": {"prompt": "Write README update"}}
    result = subprocess.run(
        ["bash", str(project_root / "hooks" / "pre-agent-snapshot.sh")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={
            "CLAUDE_PROJECT_DIR": str(repo),
            "COGNITIVE_OS_PROJECT_DIR": str(repo),
            "COGNITIVE_OS_SESSION_ID": "s1",
            "COS_AGENT_LIFECYCLE_MODE": "worktree",
        },
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    assert subprocess.run(["git", "-C", str(repo), "stash", "list"], capture_output=True, text=True).stdout == ""
    assert (repo / "README.md").read_text(encoding="utf-8") == "dirty\n"
