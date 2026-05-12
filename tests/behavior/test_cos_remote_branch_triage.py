from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
TRIAGE = REPO_ROOT / "scripts" / "cos-remote-branch-triage"


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check, timeout=30)


@pytest.fixture
def repo_with_remote(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    run(["git", "init", "--bare", str(remote)], tmp_path)
    repo = tmp_path / "repo"
    run(["git", "clone", str(remote), str(repo)], tmp_path)
    run(["git", "switch", "-c", "main"], repo)
    run(["git", "config", "user.email", "test@example.invalid"], repo)
    run(["git", "config", "user.name", "Test User"], repo)
    (repo / "README.md").write_text("root\n", encoding="utf-8")
    run(["git", "add", "README.md"], repo)
    run(["git", "commit", "-m", "initial"], repo)
    run(["git", "push", "-u", "origin", "main"], repo)
    return repo, remote


def commit_file(repo: Path, rel: str, content: str, message: str) -> str:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    run(["git", "add", rel], repo)
    run(["git", "commit", "-m", message], repo)
    return run(["git", "rev-parse", "HEAD"], repo).stdout.strip()


def triage(repo: Path, branch: str, expected_returncode: int = 0) -> dict:
    result = run(
        [str(TRIAGE), "--project-dir", str(repo), "--target", "origin/main", "--branch", branch, "--json"],
        repo,
        check=False,
    )
    assert result.returncode == expected_returncode, result.stderr
    return json.loads(result.stdout)


def test_triage_marks_patch_equivalent_remote_branch_safe_to_delete(repo_with_remote: tuple[Path, Path]) -> None:
    repo, _remote = repo_with_remote
    run(["git", "switch", "-c", "backup/equivalent"], repo)
    duplicate = commit_file(repo, "applied.txt", "same patch\n", "backup patch")
    run(["git", "push", "origin", "backup/equivalent"], repo)
    run(["git", "switch", "main"], repo)
    commit_file(repo, "applied.txt", "same patch\n", "main equivalent")
    run(["git", "push", "origin", "main"], repo)
    run(["git", "fetch", "--prune", "origin"], repo)

    payload = triage(repo, "backup/equivalent")
    finding = payload["findings"][0]

    assert payload["summary"]["safe_to_delete"] == 1
    assert finding["safe_to_delete"] is True
    assert finding["commits"][0]["sha"] == duplicate
    assert finding["commits"][0]["patch_equivalent_on_target"] is True
    assert finding["delete_command"] == "git push origin :backup/equivalent"


def test_triage_blocks_remote_branch_with_unique_patch(repo_with_remote: tuple[Path, Path]) -> None:
    repo, _remote = repo_with_remote
    run(["git", "switch", "-c", "feature/needed"], repo)
    needed = commit_file(repo, "needed.txt", "needed\n", "needed patch")
    run(["git", "push", "origin", "feature/needed"], repo)
    run(["git", "switch", "main"], repo)
    run(["git", "fetch", "--prune", "origin"], repo)

    payload = triage(repo, "feature/needed", expected_returncode=1)
    finding = payload["findings"][0]

    assert payload["summary"]["safe_to_delete"] == 0
    assert payload["summary"]["needs_port"] == 1
    assert finding["safe_to_delete"] is False
    assert finding["commits"][0]["sha"] == needed
    assert finding["commits"][0]["needs_port"] is True


def test_delete_requires_yes(repo_with_remote: tuple[Path, Path]) -> None:
    repo, _remote = repo_with_remote
    run(["git", "switch", "-c", "backup/delete-me"], repo)
    commit_file(repo, "done.txt", "done\n", "backup done")
    run(["git", "push", "origin", "backup/delete-me"], repo)
    run(["git", "switch", "main"], repo)
    commit_file(repo, "done.txt", "done\n", "main done")
    run(["git", "push", "origin", "main"], repo)
    run(["git", "fetch", "--prune", "origin"], repo)

    result = run(
        [str(TRIAGE), "--project-dir", str(repo), "--target", "origin/main", "--branch", "backup/delete-me", "--delete", "--json"],
        repo,
        check=False,
    )

    assert result.returncode != 0
    assert "Refusing deletion without --yes" in result.stderr
