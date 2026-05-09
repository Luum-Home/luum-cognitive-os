from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WRAP = ROOT / "scripts" / "cos-filter-repo-wrap.sh"


def init_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "init", "--initial-branch=main", str(repo)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    (repo / "file.txt").write_text("secret\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-u", "origin", "HEAD:main"], check=True, stdout=subprocess.DEVNULL)
    return repo, remote


def fake_filter_repo_bin(tmp_path: Path) -> Path:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    tool = bindir / "git-filter-repo"
    tool.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "git remote remove origin 2>/dev/null || true\n"
        "git config --unset branch.main.remote 2>/dev/null || true\n"
        "git config --unset branch.main.merge 2>/dev/null || true\n"
        "git update-ref -d refs/remotes/origin/main 2>/dev/null || true\n"
        "exit 0\n",
        encoding="utf-8",
    )
    tool.chmod(0o755)
    return bindir


def test_wrapper_restores_origin_and_writes_recovery(tmp_path: Path) -> None:
    repo, remote = init_repo(tmp_path)
    rules = tmp_path / "rules.txt"
    rules.write_text("secret==>redacted\n", encoding="utf-8")
    recovery = tmp_path / "recovery.json"
    env = os.environ.copy()
    env["PATH"] = f"{fake_filter_repo_bin(tmp_path)}:{env['PATH']}"

    proc = subprocess.run(
        ["bash", str(WRAP), "--project-dir", str(repo), "--rules", str(rules), "--backup-mirror", str(tmp_path / "backup.git"), "--recovery-json", str(recovery)],
        text=True,
        capture_output=True,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    assert subprocess.check_output(["git", "-C", str(repo), "remote", "get-url", "origin"], text=True).strip() == str(remote)
    assert subprocess.check_output(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], text=True).strip() == "origin/main"
    payload = json.loads(recovery.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "cos-filter-repo-recovery/v1"
    assert payload["pre_head"]
    assert payload["post_head"]
    assert payload["rules_hash"]
    assert payload["backup_mirror_path"] == str(tmp_path / "backup.git")
    assert payload["branch_upstream_restore"]["restored"] == ["main"]
    assert payload["branch_upstream_restore"]["errors"] == []


def test_wrapper_refuses_same_head_rules_env_rerun_without_force(tmp_path: Path) -> None:
    repo, _ = init_repo(tmp_path)
    rules = tmp_path / "rules.txt"
    rules.write_text("secret==>redacted\n", encoding="utf-8")
    env = os.environ.copy()
    env["PATH"] = f"{fake_filter_repo_bin(tmp_path)}:{env['PATH']}"
    cmd = ["bash", str(WRAP), "--project-dir", str(repo), "--rules", str(rules)]

    first = subprocess.run(cmd, text=True, capture_output=True, env=env)
    second = subprocess.run(cmd, text=True, capture_output=True, env=env)
    forced = subprocess.run(cmd + ["--force-re-run"], text=True, capture_output=True, env=env)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 2
    assert "refusing idempotent re-run" in second.stderr
    assert forced.returncode == 0, forced.stderr


def test_wrapper_dry_run_is_json_and_does_not_require_tool(tmp_path: Path) -> None:
    repo, _ = init_repo(tmp_path)
    rules = tmp_path / "rules.txt"
    rules.write_text("secret==>redacted\n", encoding="utf-8")
    proc = subprocess.run(["bash", str(WRAP), "--project-dir", str(repo), "--rules", str(rules), "--dry-run"], text=True, capture_output=True)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "cos-filter-repo-wrap-plan/v1"
    assert payload["status"] == "dry-run"
    assert payload["branch_upstreams"]["branches"]["main"]["remote"] == "origin"
