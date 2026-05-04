from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCTOR = REPO_ROOT / "scripts" / "cos-doctor-work-inventory.sh"


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


def commit_file(project: Path, path: str, content: str, message: str) -> str:
    target = project / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    run(["git", "add", path], project)
    run(["git", "commit", "-m", message], project)
    return run(["git", "rev-parse", "HEAD"], project).stdout.strip()


def inventory(project: Path, *extra: str, check: bool = False) -> dict:
    result = run(["bash", str(DOCTOR), "--project-dir", str(project), "--json", *extra], project, check=check)
    return json.loads(result.stdout)


def finding_codes(payload: dict) -> set[str]:
    return {finding["code"] for finding in payload["findings"]}


@pytest.mark.behavior
def test_inventory_reports_dirty_worktree_and_untracked_files(repo: Path) -> None:
    (repo / "README.md").write_text("root\nchanged\n", encoding="utf-8")
    (repo / "notes.txt").write_text("untracked\n", encoding="utf-8")

    payload = inventory(repo)

    assert payload["status"]["is_dirty"] is True
    assert payload["status"]["counts"]["modified"] == 1
    assert payload["status"]["counts"]["untracked"] == 1
    assert "worktree-dirty" in finding_codes(payload)
    assert payload["summary"]["warnings"] >= 1


@pytest.mark.behavior
def test_inventory_reports_preserve_branch_manifest_and_integration_checklist(repo: Path) -> None:
    run(["git", "checkout", "-b", "codex/preserve-mixed"], repo)
    commit_file(repo, "docs/note.md", "note\n", "docs change")
    commit_file(repo, "lib/tool.py", "print('x')\n", "lib change")
    run(["git", "checkout", "main"], repo)

    payload = inventory(repo)
    branch = payload["preserve_branches"][0]

    assert branch["branch"] == "codex/preserve-mixed"
    assert branch["manifest_exists"] is False
    assert branch["tip_is_ancestor_of_base"] is False
    assert set(branch["categories"]) >= {"docs", "lib"}
    assert {"preserve-manifest-missing", "preserve-mixed-scope", "preserve-not-integrated"} <= finding_codes(payload)


@pytest.mark.behavior
def test_inventory_reports_linked_dirty_worktree(repo: Path, tmp_path: Path) -> None:
    worktree = tmp_path / "linked-worktree"
    run(["git", "worktree", "add", "-b", "feature/wip", str(worktree), "HEAD"], repo)
    (worktree / "README.md").write_text("linked dirty\n", encoding="utf-8")

    payload = inventory(repo)

    linked = [item for item in payload["worktrees"] if item["path"] == str(worktree.resolve())]
    assert linked
    assert linked[0]["dirty"] is True
    assert "linked-worktree-dirty" in finding_codes(payload)
    finding = next(item for item in payload["findings"] if item["code"] == "linked-worktree-dirty")
    assert finding["level"] == "WARN"
    assert payload["summary"]["warnings"] >= 1


@pytest.mark.behavior
def test_direct_worktree_inventory_includes_dirty_counts(repo: Path, tmp_path: Path) -> None:
    worktree = tmp_path / "direct-linked-worktree"
    run(["git", "worktree", "add", "-b", "feature/direct-wip", str(worktree), "HEAD"], repo)
    (worktree / "README.md").write_text("direct dirty\n", encoding="utf-8")

    payload = inventory(repo, "--worktrees")

    direct = [item for item in payload["worktrees_direct"] if item["path"] == str(worktree.resolve())]
    assert direct
    assert direct[0]["dirty"] is True
    assert direct[0]["dirty_counts"]["modified"] == 1
    assert "linked-worktree-dirty" in finding_codes(payload)


@pytest.mark.behavior
def test_inventory_reports_stashes_checked_from_each_worktree(repo: Path, tmp_path: Path) -> None:
    worktree = tmp_path / "stash-linked-worktree"
    run(["git", "worktree", "add", "-b", "feature/stash-wip", str(worktree), "HEAD"], repo)
    (worktree / "linked-stash.txt").write_text("hidden from linked\n", encoding="utf-8")
    run(["git", "add", "linked-stash.txt"], worktree)
    run(["git", "stash", "push", "-m", "linked hidden work"], worktree)

    payload = inventory(repo)

    groups = {item["worktree_path"]: item for item in payload["worktree_stashes"]}
    assert str(repo.resolve()) in groups
    assert str(worktree.resolve()) in groups
    assert groups[str(worktree.resolve())]["stash_count"] == 1
    assert "linked-worktree-stashes-present" in finding_codes(payload)
    finding = next(item for item in payload["findings"] if item["code"] == "linked-worktree-stashes-present")
    assert finding["level"] == "BLOCK"


@pytest.mark.behavior
def test_inventory_reports_stashes_even_when_not_auto_pre_agent(repo: Path) -> None:
    (repo / "stash.txt").write_text("hidden\n", encoding="utf-8")
    run(["git", "add", "stash.txt"], repo)
    run(["git", "stash", "push", "-m", "manual hidden work"], repo)

    payload = inventory(repo, "--stash-warn-ttl", "0", "--stash-block-ttl", "999999")

    assert payload["summary"]["stash_count"] == 1
    assert payload["stashes"][0]["subject"].endswith("manual hidden work")
    assert payload["stashes"][0]["level"] == "WARN"
    assert "stash-aged" in finding_codes(payload)


@pytest.mark.behavior
def test_inventory_strict_exits_nonzero_for_warnings(repo: Path) -> None:
    (repo / "wip.txt").write_text("wip\n", encoding="utf-8")

    result = run(["bash", str(DOCTOR), "--project-dir", str(repo), "--strict"], repo, check=False)

    assert result.returncode == 1
    assert "WARN worktree-dirty" in result.stdout
