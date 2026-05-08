from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "push_collision_detect.py"


def setup_rewritten_repo(tmp_path: Path) -> tuple[Path, str, str]:
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "init", "--initial-branch=main", str(repo)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    (repo / "a.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "a.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "same subject"], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-u", "origin", "main"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pre = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    (repo / "b.txt").write_text("different local work\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "b.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "same subject"], check=True, stdout=subprocess.DEVNULL)
    post = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    return repo, pre, post


def write_marker(repo: Path, pre: str, post: str, *, expired: bool = False) -> None:
    runtime = repo / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)
    now = datetime.now(timezone.utc)
    expires = now - timedelta(seconds=1) if expired else now + timedelta(hours=1)
    (runtime / "last-rewrite.json").write_text(json.dumps({
        "schema_version": "cos-last-rewrite/v1",
        "pre_head": pre,
        "post_head": post,
        "rewritten_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ttl_seconds": 3600,
        "rules_hash": "abc123",
    }), encoding="utf-8")


def run_detector(repo: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["COS_PUSH_COLLISION_MODE"] = "block"
    return subprocess.run(["python3", str(SCRIPT), "--project-dir", str(repo), "--json"], text=True, capture_output=True, env=env)


def test_post_rewrite_marker_allows_subject_collision(tmp_path: Path) -> None:
    repo, pre, post = setup_rewritten_repo(tmp_path)
    write_marker(repo, pre, post)

    proc = run_detector(repo)

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["post_rewrite_exception"]["reason"] == "post-rewrite-marker-match"
    assert payload["collisions"]


def test_without_marker_collision_still_blocks(tmp_path: Path) -> None:
    repo, _, _ = setup_rewritten_repo(tmp_path)

    proc = run_detector(repo)

    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False


def test_expired_marker_falls_back_to_block(tmp_path: Path) -> None:
    repo, pre, post = setup_rewritten_repo(tmp_path)
    write_marker(repo, pre, post, expired=True)

    proc = run_detector(repo)

    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["post_rewrite_exception"]["reason"] == "marker-expired"
