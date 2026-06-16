from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    if check and result.returncode != 0:
        raise AssertionError(f"command failed {cmd}:\nSTDOUT={result.stdout}\nSTDERR={result.stderr}")
    return result


def init_repo(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    run(["git", "init", "--bare", str(remote)], tmp_path)
    repo = tmp_path / "repo"
    run(["git", "clone", str(remote), str(repo)], tmp_path)
    run(["git", "config", "user.email", "test@example.com"], repo)
    run(["git", "config", "user.name", "Test User"], repo)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    run(["git", "add", "README.md"], repo)
    run(["git", "commit", "-m", "base"], repo)
    run(["git", "push", "origin", "main"], repo)
    run(["git", "checkout", "-b", "codex/done"], repo)
    (repo / "done.txt").write_text("done\n", encoding="utf-8")
    run(["git", "add", "done.txt"], repo)
    run(["git", "commit", "-m", "done"], repo)
    run(["git", "push", "origin", "codex/done"], repo)
    run(["git", "checkout", "main"], repo)
    run(["git", "merge", "--ff-only", "codex/done"], repo)
    run(["git", "push", "origin", "main"], repo)
    run(["git", "checkout", "-b", "codex/open"], repo)
    (repo / "open.txt").write_text("open\n", encoding="utf-8")
    run(["git", "add", "open.txt"], repo)
    run(["git", "commit", "-m", "open"], repo)
    run(["git", "checkout", "main"], repo)
    return repo


def test_closure_report_classifies_merged_and_useful_branches(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    result = run([str(REPO / "scripts" / "cos-branch-worktree-closure"), "--project-dir", str(repo), "--json"], repo)
    payload = json.loads(result.stdout)

    by_branch = {row["branch"]: row for row in payload["branches"]}
    assert by_branch["codex/done"]["classification"] == "merged-cleanup"
    assert by_branch["codex/open"]["classification"] == "useful-land-required"
    assert "codex/done" in payload["remote_merged_branches"]
    assert payload["batch_remote_delete_command"] == "git push origin :refs/heads/codex/done"
    assert "scripts/cos land" in payload["landing_command"]


def test_cleanup_merged_is_dry_run_without_apply(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    result = run([str(REPO / "scripts" / "cos-branch-worktree-closure"), "--project-dir", str(repo), "--cleanup-merged", "--json"], repo)
    payload = json.loads(result.stdout)

    cleanup = payload["actions"]["cleanup_merged"]
    assert cleanup["remote_deleted"]["status"] == "dry-run"
    assert any(item["branch"] == "codex/done" and item["status"] == "dry-run" for item in cleanup["local_deleted"])
    assert run(["git", "branch", "--list", "codex/done"], repo).stdout.strip() == "codex/done"


def test_cos_router_exposes_branch_and_worktree_closure() -> None:
    help_text = run(["bash", str(REPO / "scripts" / "cos"), "--help"], REPO).stdout
    assert "cos branch closure" in help_text
    assert "cos worktree closure" in help_text
