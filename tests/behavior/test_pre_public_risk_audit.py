from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "cos-pre-public-risk-audit"


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, env=env)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "--initial-branch=main"], repo).check_returncode()
    _run(["git", "config", "user.name", "Human Author"], repo).check_returncode()
    _run(["git", "config", "user.email", "human@example.com"], repo).check_returncode()
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")
    _run(["git", "add", "README.md"], repo).check_returncode()
    _run(["git", "commit", "-m", "seed"], repo).check_returncode()
    return repo


def test_pre_public_audit_preserves_human_author_emails(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    remote = tmp_path / "origin.git"
    _run(["git", "init", "--bare", str(remote)], tmp_path).check_returncode()
    _run(["git", "remote", "add", "origin", str(remote)], repo).check_returncode()
    proc = _run([str(SCRIPT), "--repo", str(repo), "--json"], repo)

    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["checks"]["authors"] == ["Human Author <human@example.com>"]
    assert payload["checks"]["git_remotes"] == ["origin"]
    assert payload["policy"]["commit_author_emails"].startswith("preserve")
    assert not any(f["code"] == "fake-or-provider-author-metadata" for f in payload["findings"])


def test_pre_public_audit_warns_when_git_remote_missing(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    proc = _run([str(SCRIPT), "--repo", str(repo), "--json"], repo)

    assert proc.returncode == 1, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["status"] == "block"
    assert payload["checks"]["git_remotes"] == []
    assert any(f["code"] == "git-remote-missing" for f in payload["findings"])


def test_pre_public_audit_blocks_configured_sensitive_token_in_history(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    token = "private-token@example.invalid"
    (repo / "leak.txt").write_text(token + "\n", encoding="utf-8")
    _run(["git", "add", "leak.txt"], repo).check_returncode()
    _run(["git", "commit", "-m", "add leaked token"], repo).check_returncode()
    env = os.environ.copy()
    env["COS_HISTORY_SANITIZE_OPERATOR_EMAIL"] = token

    proc = _run([str(SCRIPT), "--repo", str(repo), "--json"], repo, env=env)

    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["status"] == "block"
    assert any(f["code"] == "configured-sensitive-token-in-history" for f in payload["findings"])


def test_pre_public_audit_blocks_x_cos_trailers(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "--initial-branch=main"], repo).check_returncode()
    _run(["git", "config", "user.name", "Human Author"], repo).check_returncode()
    _run(["git", "config", "user.email", "human@example.com"], repo).check_returncode()
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")
    _run(["git", "add", "README.md"], repo).check_returncode()
    _run(["git", "commit", "-m", "seed", "-m", "X-COS-Session: abc"], repo).check_returncode()

    proc = _run([str(SCRIPT), "--repo", str(repo), "--json"], repo)

    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert any(f["code"] == "x-cos-trailers-in-history" for f in payload["findings"])


def test_pre_public_audit_blocks_fake_provider_author(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "--initial-branch=main"], repo).check_returncode()
    _run(["git", "config", "user.name", "Claude"], repo).check_returncode()
    _run(["git", "config", "user.email", "noreply@anthropic.com"], repo).check_returncode()
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")
    _run(["git", "add", "README.md"], repo).check_returncode()
    _run(["git", "commit", "-m", "seed"], repo).check_returncode()

    proc = _run([str(SCRIPT), "--repo", str(repo), "--json"], repo)

    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert any(f["code"] == "fake-or-provider-author-metadata" for f in payload["findings"])
