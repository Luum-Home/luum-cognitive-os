"""Behavior tests for ADR-116 branch writer lease primitive."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "cos_branch_lease.py"
WRAPPER = REPO_ROOT / "scripts" / "cos-branch-lease"


def run_cli(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(project), *args, "--json"],
        text=True,
        capture_output=True,
        check=False,
    )


def payload(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)


def test_acquire_blocks_second_writer_on_same_branch(tmp_path: Path) -> None:
    first = run_cli(tmp_path, "acquire", "--branch", "feature/x", "--owner", "agent-a", "--session-id", "s1")
    assert first.returncode == 0

    second = run_cli(tmp_path, "acquire", "--branch", "feature/x", "--owner", "agent-b", "--session-id", "s2")
    assert second.returncode == 2
    data = payload(second)
    assert data["status"] == "blocked"
    assert data["lease"]["owner"] == "agent-a"


def test_same_owner_can_renew_lease(tmp_path: Path) -> None:
    assert run_cli(tmp_path, "acquire", "--branch", "feature/x", "--owner", "agent-a", "--session-id", "s1").returncode == 0
    renewed = run_cli(tmp_path, "acquire", "--branch", "feature/x", "--owner", "agent-a", "--session-id", "s1")
    assert renewed.returncode == 0
    assert payload(renewed)["status"] == "acquired"


def test_release_requires_owner(tmp_path: Path) -> None:
    assert run_cli(tmp_path, "acquire", "--branch", "feature/x", "--owner", "agent-a", "--session-id", "s1").returncode == 0
    denied = run_cli(tmp_path, "release", "--branch", "feature/x", "--owner", "agent-b", "--session-id", "s2")
    assert denied.returncode == 2
    assert payload(denied)["status"] == "blocked"

    released = run_cli(tmp_path, "release", "--branch", "feature/x", "--owner", "agent-a", "--session-id", "s1")
    assert released.returncode == 0
    assert payload(released)["status"] == "released"


def test_expired_lease_is_pruned_and_allows_new_writer(tmp_path: Path) -> None:
    assert run_cli(
        tmp_path,
        "acquire",
        "--branch",
        "feature/x",
        "--owner",
        "agent-a",
        "--session-id",
        "s1",
        "--ttl-seconds",
        "0",
    ).returncode == 0
    second = run_cli(tmp_path, "acquire", "--branch", "feature/x", "--owner", "agent-b", "--session-id", "s2")
    assert second.returncode == 0
    assert payload(second)["lease"]["owner"] == "agent-b"


def test_check_blocks_non_owner_when_branch_is_leased(tmp_path: Path) -> None:
    assert run_cli(tmp_path, "acquire", "--branch", "feature/x", "--owner", "agent-a", "--session-id", "s1").returncode == 0
    checked = run_cli(tmp_path, "check", "--branch", "feature/x", "--owner", "agent-b", "--session-id", "s2")
    assert checked.returncode == 2
    assert payload(checked)["reason"] == "branch is leased by another writer"


def test_wrapper_has_valid_bash_syntax() -> None:
    result = subprocess.run(["bash", "-n", str(WRAPPER)], text=True, capture_output=True, check=False)
    assert result.returncode == 0
