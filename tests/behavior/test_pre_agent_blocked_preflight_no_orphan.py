from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "tracked.txt").write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


@pytest.mark.behavior
def test_planned_snapshot_plus_blocked_later_preflight_creates_no_stash(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    payload = json.dumps({"tool_name": "Agent", "tool_use_id": "toolu_test", "tool_input": {"prompt": "test"}})
    env = os.environ.copy()
    env.update({"CLAUDE_PROJECT_DIR": str(repo), "COGNITIVE_OS_SESSION_ID": "s1", "PYTHONPATH": str(REPO_ROOT)})

    subprocess.run([str(REPO_ROOT / "hooks" / "pre-agent-snapshot.sh")], input=payload, text=True, env=env, check=True)

    stash_before_restore = subprocess.run(["git", "stash", "list"], cwd=repo, capture_output=True, text=True, check=True).stdout
    assert stash_before_restore == ""
    assert (repo / ".cognitive-os" / "runtime" / "pre-agent-plan-toolu_test.json").exists()

    subprocess.run([str(REPO_ROOT / "hooks" / "post-agent-snapshot-restore.sh")], input=payload, text=True, env=env, check=True)

    stash_after_restore = subprocess.run(["git", "stash", "list"], cwd=repo, capture_output=True, text=True, check=True).stdout
    assert stash_after_restore == ""
    assert not (repo / ".cognitive-os" / "runtime" / "pre-agent-plan-toolu_test.json").exists()


@pytest.mark.behavior
def test_confirmed_launch_commits_plan_then_restore_drops_auto_stash(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    payload = json.dumps({"tool_name": "Agent", "tool_use_id": "toolu_ok", "tool_input": {"prompt": "test"}})
    env = os.environ.copy()
    env.update({"CLAUDE_PROJECT_DIR": str(repo), "COGNITIVE_OS_SESSION_ID": "s1", "PYTHONPATH": str(REPO_ROOT)})

    subprocess.run([str(REPO_ROOT / "hooks" / "pre-agent-snapshot.sh")], input=payload, text=True, env=env, check=True)
    subprocess.run([str(REPO_ROOT / "hooks" / "agent-launch-confirmed.sh")], input=payload, text=True, env=env, check=True)

    assert "auto-pre-agent-toolu_ok" in subprocess.run(["git", "stash", "list"], cwd=repo, capture_output=True, text=True, check=True).stdout
    marker = repo / ".cognitive-os" / "runtime" / "pre-agent-snapshot-toolu_ok.json"
    assert json.loads(marker.read_text())["stash_sha"]

    subprocess.run([str(REPO_ROOT / "hooks" / "post-agent-snapshot-restore.sh")], input=payload, text=True, env=env, check=True)

    assert subprocess.run(["git", "stash", "list"], cwd=repo, capture_output=True, text=True, check=True).stdout == ""
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "dirty\n"
