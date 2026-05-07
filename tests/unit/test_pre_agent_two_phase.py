from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from lib.snapshot_manager import commit_snapshot_plan, plan_snapshot, sweep_snapshot_plans


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "tracked.txt").write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


def _stash_list(repo: Path) -> str:
    return subprocess.run(["git", "stash", "list"], cwd=repo, capture_output=True, text=True, check=True).stdout


@pytest.mark.unit
def test_phase_1_plan_does_not_create_stash(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    before = _stash_list(repo)

    plan = plan_snapshot(repo, "agent-1")

    assert _stash_list(repo) == before
    assert plan["schema_version"] == "pre-agent-snapshot-plan/v1"
    assert plan["tracked_files"] == ["tracked.txt"]
    assert plan["untracked_files"] == ["new.txt"]
    assert (Path(plan["snapshot_dir"]) / "new.txt").read_text(encoding="utf-8") == "new\n"


@pytest.mark.unit
def test_phase_2_commit_requires_plan_and_stashes_by_sha(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    plan = plan_snapshot(repo, "agent-2")

    committed = commit_snapshot_plan(repo, plan)

    assert committed["schema_version"] == "pre-agent-snapshot/v2"
    assert committed["tracked_stash_sha"]
    assert committed["status"] == "stashed"
    assert "auto-pre-agent-agent-2" in _stash_list(repo)
    with pytest.raises(ValueError):
        commit_snapshot_plan(repo, {"schema_version": "wrong"})


@pytest.mark.unit
def test_sweep_snapshot_plans_deletes_stale_plan_without_marker(tmp_path: Path) -> None:
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)
    plan = runtime / "pre-agent-plan-a1.json"
    plan.write_text(json.dumps({"agent_id": "a1"}), encoding="utf-8")

    deleted = sweep_snapshot_plans(tmp_path, ttl_seconds=0)

    assert deleted == [str(plan)]
    assert not plan.exists()
