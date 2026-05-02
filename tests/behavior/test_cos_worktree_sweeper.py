from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMPL = PROJECT_ROOT / "scripts" / "cos_worktree_sweeper.py"
WRAPPER = PROJECT_ROOT / "scripts" / "cos_worktree_sweeper.py"


def run(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(args, cwd=str(cwd), env=merged, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], repo)


def init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git(repo, "init").returncode == 0
    assert git(repo, "config", "user.email", "test@example.com").returncode == 0
    assert git(repo, "config", "user.name", "Test User").returncode == 0
    (repo / "README.md").write_text("root\n", encoding="utf-8")
    assert git(repo, "add", "README.md").returncode == 0
    assert git(repo, "commit", "-m", "initial").returncode == 0
    return repo


def add_detached(repo: Path, path: Path) -> Path:
    result = git(repo, "worktree", "add", "--detach", str(path), "HEAD")
    assert result.returncode == 0, result.stderr
    return path


def sweep(repo: Path, safe_prefix: Path, *extra: str, env: dict[str, str] | None = None) -> dict:
    result = run([
        sys.executable,
        str(IMPL),
        "--repo",
        str(repo),
        "--ttl-seconds",
        "0",
        "--no-default-safe-prefixes",
        "--safe-prefix",
        str(safe_prefix),
        *extra,
    ], PROJECT_ROOT, {"COS_WORKTREE_SWEEPER_DISABLE_LSOF": "1", **(env or {})})
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def by_path(report: dict, path: Path) -> dict:
    for item in report["worktrees"]:
        if item["path"] == str(path.resolve()):
            return item
    raise AssertionError(f"missing report for {path}")


def test_module_is_importable_with_underscore_name() -> None:
    spec = importlib.util.spec_from_file_location("cos_worktree_sweeper", IMPL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["cos_worktree_sweeper"] = module
    spec.loader.exec_module(module)
    assert callable(module.main)


def test_wrapper_cli_delegates_to_importable_module(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    result = run([sys.executable, str(WRAPPER), "--repo", str(repo), "--dry-run", "--json"], PROJECT_ROOT, {"COS_WORKTREE_SWEEPER_DISABLE_LSOF": "1"})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["mode"] == "dry-run"


def test_dry_run_marks_detached_worktree_with_only_venv_as_candidate(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    wt = add_detached(repo, tmp_path / "laptop-wt")
    (wt / ".venv").mkdir()
    item = by_path(sweep(repo, tmp_path), wt)
    assert item["decision"] == "remove-candidate"
    assert "only_allowlisted_untracked" in item["reasons"]


def test_apply_removes_only_candidate_through_git_worktree_remove(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    wt = add_detached(repo, tmp_path / "laptop-wt")
    (wt / ".venv").mkdir()
    report = sweep(repo, tmp_path, "--apply")
    assert report["removed"][0]["removed"] is True
    assert str(wt) not in git(repo, "worktree", "list", "--porcelain").stdout
    assert not wt.exists()


def test_active_process_marker_blocks_candidate(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    wt = add_detached(repo, tmp_path / "active-wt")
    (wt / ".venv").mkdir()
    item = by_path(sweep(repo, tmp_path, env={"COS_WORKTREE_SWEEPER_FAKE_ACTIVE_PATHS": str(wt)}), wt)
    assert item["decision"] == "keep"
    assert "active_process_or_open_file" in item["blockers"]


def test_tracked_changes_block_candidate(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    wt = add_detached(repo, tmp_path / "dirty-wt")
    (wt / "README.md").write_text("changed\n", encoding="utf-8")
    item = by_path(sweep(repo, tmp_path), wt)
    assert item["decision"] == "keep"
    assert "tracked_changes" in item["blockers"]


def test_non_allowlisted_untracked_file_blocks_candidate(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    wt = add_detached(repo, tmp_path / "notes-wt")
    (wt / "notes.txt").write_text("human notes\n", encoding="utf-8")
    item = by_path(sweep(repo, tmp_path), wt)
    assert item["decision"] == "keep"
    assert "non_allowlisted_untracked" in item["blockers"]


def test_branch_worktree_is_not_removed(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    wt = tmp_path / "branch-wt"
    assert git(repo, "worktree", "add", "-b", "feature", str(wt), "HEAD").returncode == 0
    item = by_path(sweep(repo, tmp_path), wt)
    assert item["decision"] == "keep"
    assert "branch_worktree" in item["blockers"]


def test_outside_safe_prefix_blocks_candidate(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    wt = add_detached(repo, tmp_path / "outside-parent" / "outside-wt")
    item = by_path(sweep(repo, tmp_path / "different-safe-prefix"), wt)
    assert item["decision"] == "keep"
    assert "outside_safe_prefix" in item["blockers"]
