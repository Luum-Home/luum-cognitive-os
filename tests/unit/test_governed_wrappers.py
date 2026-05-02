"""Tests for Codex/VS Code governed wrappers."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOVERNED_AGENT = PROJECT_ROOT / "scripts" / "cos-governed-agent.sh"
GOVERNED_EDIT = PROJECT_ROOT / "scripts" / "cos-governed-edit.sh"
COS_TASK_CLAIMS = PROJECT_ROOT / "scripts" / "cos_task_claims.py"

pytestmark = pytest.mark.unit


def init_synced_repo(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", str(remote), str(repo)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("# test\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "push", "-u", "origin", "HEAD:main"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return repo


def env_for(repo: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env["COGNITIVE_OS_SESSION_ID"] = "session-test"
    # Avoid inherited repo hooks or operator state affecting isolated tests.
    env.pop("COS_SKIP_GOVERNED_INVENTORY", None)
    return env


def test_governed_agent_runs_claim_and_inventory(tmp_path: Path) -> None:
    repo = init_synced_repo(tmp_path)
    proc = subprocess.run(
        [
            "bash",
            str(GOVERNED_AGENT),
            "--task-id",
            "TASK-1",
            "--scope",
            "implement isolated governed wrapper test",
            "--session-id",
            "session-a",
            "--agent-id",
            "agent-a",
            "--",
            "true",
        ],
        cwd=repo,
        env=env_for(repo),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    claims = json.loads((repo / ".cognitive-os" / "tasks" / "active-claims.json").read_text())
    assert any(c["task_id"] == "TASK-1" and c["status"] == "completed" for c in claims["claims"])


def test_governed_agent_blocks_duplicate_active_claim(tmp_path: Path) -> None:
    repo = init_synced_repo(tmp_path)
    subprocess.run(
        [
            "python3",
            str(COS_TASK_CLAIMS),
            "--project-dir",
            str(repo),
            "claim",
            "--task-id",
            "TASK-2",
            "--description",
            "same work",
            "--session-id",
            "other-session",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    proc = subprocess.run(
        [
            "bash",
            str(GOVERNED_AGENT),
            "--task-id",
            "TASK-2",
            "--scope",
            "same work",
            "--session-id",
            "session-b",
            "--agent-id",
            "agent-b",
            "--",
            "true",
        ],
        cwd=repo,
        env=env_for(repo),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 2
    assert "ACTIVE TASK CLAIM BLOCK" in proc.stderr


def test_governed_edit_requires_task_id(tmp_path: Path) -> None:
    repo = init_synced_repo(tmp_path)
    proc = subprocess.run(
        ["bash", str(GOVERNED_EDIT), "--file", "README.md", "--", "true"],
        cwd=repo,
        env=env_for(repo),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 2
    assert "--task-id is required" in proc.stderr
