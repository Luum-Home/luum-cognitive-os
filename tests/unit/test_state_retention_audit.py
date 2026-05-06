"""Unit tests for ADR-199 state retention audit and stash cleanup."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "state_retention_audit.py"
MANIFEST = ROOT / "manifests" / "state-retention.yaml"


def run_cmd(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, env=merged)


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = run_cmd(["git", *args], repo, env=env)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test User")
    (tmp_path / "README.md").write_text("base\n", encoding="utf-8")
    git(tmp_path, "add", "README.md")
    git(tmp_path, "commit", "-m", "initial")
    return tmp_path


def make_stash(repo: Path, name: str, filename: str, content: str, hours_ago: int = 2) -> None:
    # git stash does not include untracked files by default; track each test file
    # first so the retention path exercises normal tracked WIP stashes.
    target = repo / filename
    target.write_text("base\n", encoding="utf-8")
    git(repo, "add", filename)
    git(repo, "commit", "-m", f"track {filename}")
    target.write_text(content, encoding="utf-8")
    stamp = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%S +0000")
    git(repo, "stash", "push", "-m", name, env={"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp})


def manifest_with_zero_stash_ttl(tmp_path: Path) -> Path:
    text = MANIFEST.read_text(encoding="utf-8")
    text = text.replace("max_age: P1H", "max_age: P0H", 1)
    manifest = tmp_path / "state-retention.yaml"
    manifest.write_text(text, encoding="utf-8")
    return manifest


def run_audit(repo: Path, *args: str, manifest: Path = MANIFEST) -> subprocess.CompletedProcess[str]:
    return run_cmd([sys.executable, str(SCRIPT), "--project-dir", str(repo), "--manifest", str(manifest), *args], ROOT)


def parse_json(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.returncode in (0, 2), result.stderr
    return json.loads(result.stdout)


def test_manifest_declares_required_surface_fields() -> None:
    result = run_audit(ROOT, "--json", "--no-metrics")
    payload = parse_json(result)
    assert payload["manifest_findings"] == []
    surfaces = {surface["surface"] for surface in payload["surfaces"]}
    assert "auto-pre-agent-stashes" in surfaces
    assert "task-claims-ledger" in surfaces
    assert "agent-bus-directories" in surfaces


def test_stash_cleanup_preview_selects_only_stale_auto_pre_agent(git_repo: Path, tmp_path: Path) -> None:
    make_stash(git_repo, "manual-preserve-important", "manual.txt", "manual\n")
    make_stash(git_repo, "auto-pre-agent-toolu_abc", "auto.txt", "auto\n")
    time.sleep(1.1)

    result = run_audit(git_repo, "--surface", "auto-pre-agent-stashes", "--reap", "--json", "--no-metrics", manifest=manifest_with_zero_stash_ttl(tmp_path))
    payload = parse_json(result)

    assert payload["reap"][0]["candidate_count"] == 1
    actions = payload["reap"][0]["actions"]
    assert len(actions) == 1
    assert "auto-pre-agent-toolu_abc" in actions[0]["subject"]
    assert actions[0]["execute"] is False
    assert "manual-preserve-important" not in json.dumps(actions)

    stash_list = git(git_repo, "stash", "list").stdout
    assert "manual-preserve-important" in stash_list
    assert "auto-pre-agent-toolu_abc" in stash_list


def test_stash_cleanup_execute_archives_then_drops_only_auto_stash(git_repo: Path, tmp_path: Path) -> None:
    make_stash(git_repo, "manual-preserve-important", "manual.txt", "manual\n")
    make_stash(git_repo, "auto-pre-agent-toolu_abc", "auto.txt", "auto\n")
    time.sleep(1.1)

    result = run_audit(git_repo, "--surface", "auto-pre-agent-stashes", "--reap", "--execute", "--json", "--no-metrics", manifest=manifest_with_zero_stash_ttl(tmp_path))
    payload = parse_json(result)
    action = payload["reap"][0]["actions"][0]

    assert action["dropped"] is True
    assert action["preserved_ref"].startswith("refs/cos-preserved-stash/")
    assert (git_repo / action["patch"]).is_file()
    assert (git_repo / action["name_status"]).is_file()
    assert git(git_repo, "rev-parse", action["preserved_ref"]).stdout.strip() == action["sha"]

    stash_list = git(git_repo, "stash", "list").stdout
    assert "auto-pre-agent-toolu_abc" not in stash_list
    assert "manual-preserve-important" in stash_list


def test_claim_ledger_compaction_dry_run_reports_terminal_records(git_repo: Path) -> None:
    claims_path = git_repo / ".cognitive-os" / "tasks" / "active-claims.json"
    claims_path.parent.mkdir(parents=True)
    old = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    claims_path.write_text(json.dumps({"claims": [{"task_id": "a", "status": "released", "released_at": old}, {"task_id": "b", "status": "active"}]}) + "\n", encoding="utf-8")

    result = run_audit(git_repo, "--surface", "task-claims-ledger", "--reap", "--json", "--no-metrics")
    payload = parse_json(result)

    assert payload["surfaces"][0]["old_terminal_count"] == 1
    assert payload["reap"][0]["removed"] == 1
    assert json.loads(claims_path.read_text(encoding="utf-8"))["claims"][0]["task_id"] == "a"


def test_auto_safe_selects_only_repair_safe_surfaces(git_repo: Path) -> None:
    claims_path = git_repo / ".cognitive-os" / "tasks" / "active-claims.json"
    claims_path.parent.mkdir(parents=True)
    old = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    claims_path.write_text(json.dumps({"claims": [{"task_id": "a", "status": "released", "released_at": old}]}) + "\n", encoding="utf-8")
    bus_dir = git_repo / ".cognitive-os" / "agent-bus" / "old-agent"
    bus_dir.mkdir(parents=True)

    result = run_audit(git_repo, "--auto-safe", "--reap", "--json", "--no-metrics")
    payload = parse_json(result)

    surfaces = {surface["surface"] for surface in payload["surfaces"]}
    assert surfaces == {"task-claims-ledger", "agent-bus-directories"}
    assert {item["surface"] for item in payload["reap"]} == {"task-claims-ledger", "agent-bus-directories"}


def test_repair_before_block_selects_only_auto_stash_surface(git_repo: Path, tmp_path: Path) -> None:
    make_stash(git_repo, "auto-pre-agent-toolu_repair", "repair.txt", "repair\n")
    time.sleep(1.1)

    result = run_audit(
        git_repo,
        "--repair-before-block",
        "--reap",
        "--json",
        "--no-metrics",
        manifest=manifest_with_zero_stash_ttl(tmp_path),
    )
    payload = parse_json(result)

    assert [surface["surface"] for surface in payload["surfaces"]] == ["auto-pre-agent-stashes"]
    assert payload["reap"][0]["candidate_count"] == 1
