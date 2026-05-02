from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
TRIAGE = REPO_ROOT / "scripts" / "cos-worktree-triage.sh"


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check, timeout=30)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    run(["git", "init", "-b", "main"], project)
    run(["git", "config", "user.email", "test@example.invalid"], project)
    run(["git", "config", "user.name", "Test User"], project)
    (project / "README.md").write_text("root\n", encoding="utf-8")
    run(["git", "add", "README.md"], project)
    run(["git", "commit", "-m", "initial"], project)
    return project


def commit_file(repo: Path, rel: str, content: str, message: str) -> str:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    run(["git", "add", rel], repo)
    run(["git", "commit", "-m", message], repo)
    return run(["git", "rev-parse", "HEAD"], repo).stdout.strip()


def triage(project: Path, worktree: Path, check: bool = False) -> dict:
    result = run(
        ["bash", str(TRIAGE), "--project-dir", str(project), "--worktree", str(worktree), "--target", "main", "--json"],
        project,
        check=check,
    )
    return json.loads(result.stdout)


def test_triage_marks_patch_equivalent_commits_as_already_applied(repo: Path, tmp_path: Path) -> None:
    worktree = tmp_path / "bb5a"
    run(["git", "worktree", "add", "-b", "feature/bb5a", str(worktree), "HEAD"], repo)
    duplicate = commit_file(worktree, "applied.txt", "same patch\n", "feature already applied")
    commit_file(repo, "applied.txt", "same patch\n", "equivalent already on main")
    needed = commit_file(worktree, "needed.txt", "new patch\n", "feature still needed")

    payload = triage(repo, worktree)

    assert [item["sha"] for item in payload["already_applied_commits"]] == [duplicate]
    assert [item["sha"] for item in payload["commits_to_port"]] == [needed]
    assert any(command == f"git cherry-pick {needed}" for command in payload["suggested_commands"])
    assert payload["safe_to_remove"] is False


def test_triage_blocks_dirty_worktree_and_stashes(repo: Path, tmp_path: Path) -> None:
    worktree = tmp_path / "bb5a-dirty"
    run(["git", "worktree", "add", "-b", "feature/dirty", str(worktree), "HEAD"], repo)
    (worktree / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    run(["git", "add", "dirty.txt"], worktree)
    run(["git", "stash", "push", "-m", "hidden bb5a work"], worktree)
    (worktree / "untracked.txt").write_text("untracked\n", encoding="utf-8")

    payload = triage(repo, worktree)
    codes = {item["code"] for item in payload["blockers"]}

    assert {"worktree-dirty", "worktree-stashes-present"} <= codes
    assert payload["safe_to_remove"] is False
    assert any("stash show --name-status" in command for command in payload["suggested_commands"])


def test_triage_reports_safe_to_remove_when_clean_and_fully_applied(repo: Path, tmp_path: Path) -> None:
    worktree = tmp_path / "bb5a-clean"
    run(["git", "worktree", "add", "-b", "feature/clean", str(worktree), "HEAD"], repo)
    commit_file(worktree, "done.txt", "done\n", "done elsewhere")
    commit_file(repo, "done.txt", "done\n", "equivalent done on main")

    payload = triage(repo, worktree)

    assert payload["blockers"] == []
    assert payload["commits_to_port"] == []
    assert payload["safe_to_remove"] is True
    assert payload["suggested_commands"][-1] == f"git worktree remove {worktree.resolve()}"
