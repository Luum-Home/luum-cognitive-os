from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DETECTOR = REPO_ROOT / "scripts" / "stash-leak-alarm.sh"


def run_detector(project: Path, *, ttl: int = 0, block_ttl: int = 999999) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project)
    env["COS_STASH_LEAK_TTL"] = str(ttl)
    env["COS_STASH_LEAK_BLOCK_TTL"] = str(block_ttl)
    return subprocess.run(
        ["bash", str(DETECTOR)],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )


@pytest.fixture
def repo_with_auto_stash(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project, check=True)
    tracked = project / "tracked.txt"
    tracked.write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=project, check=True, capture_output=True)
    tracked.write_text("hidden agent work\n", encoding="utf-8")
    subprocess.run(["git", "stash", "push", "-m", "auto-pre-agent-test-scenario", "--", "tracked.txt"], cwd=project, check=True, capture_output=True)
    return project


@pytest.mark.behavior
def test_auto_pre_agent_stash_above_ttl_writes_alarm(repo_with_auto_stash: Path):
    result = run_detector(repo_with_auto_stash, ttl=0, block_ttl=999999)
    assert result.returncode == 0
    assert "WARN auto-pre-agent stash leak" in result.stdout

    alarm = repo_with_auto_stash / ".cognitive-os" / "runtime" / "stash-leak-alarm.json"
    assert alarm.exists()
    payload = json.loads(alarm.read_text(encoding="utf-8"))
    assert payload["stash_ref"].startswith("stash@{")
    assert "auto-pre-agent-test-scenario" in payload["stash_message"]
    assert payload["file_count"] == 1
    assert payload["blocking"] is False
    assert any("git stash show" in item for item in payload["remediation"])
    assert any("git stash apply" in item for item in payload["remediation"])
    assert not any("git stash pop" in item for item in payload["remediation"])


@pytest.mark.behavior
def test_auto_pre_agent_stash_blocks_when_block_ttl_exceeded(repo_with_auto_stash: Path):
    result = run_detector(repo_with_auto_stash, ttl=0, block_ttl=0)
    assert result.returncode == 2
    assert "BLOCK auto-pre-agent stash leak" in result.stdout
    assert "git stash apply" in result.stdout
    assert "after confirming ownership" in result.stdout

    alarm = repo_with_auto_stash / ".cognitive-os" / "runtime" / "stash-leak-alarm.json"
    payload = json.loads(alarm.read_text(encoding="utf-8"))
    assert payload["blocking"] is True


@pytest.mark.behavior
def test_detector_does_not_report_clean_repo(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    result = run_detector(project, ttl=0, block_ttl=0)
    assert result.returncode == 0
    assert "PASS no auto-pre-agent stash leak" in result.stdout
