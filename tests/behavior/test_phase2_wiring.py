"""Behavior tests for Phase 2 wiring of existing Cognitive OS safety primitives."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
GOVERNED_AGENT = REPO_ROOT / "scripts" / "cos-governed-agent.sh"
BRANCH_LEASE = REPO_ROOT / "scripts" / "cos_branch_lease.py"
RUN_TASK = REPO_ROOT / "scripts" / "cos_run_task.py"
SAFE_MODE = REPO_ROOT / "scripts" / "cos_headless_safe_mode.py"
RUN_TASK_WRAPPER = REPO_ROOT / "scripts" / "cos-run-task"


def init_git_project(path: Path, branch: str = "feature/phase2") -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test User"], check=True)
    subprocess.run(["git", "-C", str(path), "checkout", "-q", "-b", branch], check=True)


def json_payload(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def test_governed_agent_blocks_when_same_branch_writer_lease_exists(tmp_path: Path) -> None:
    """The governed prelaunch path refuses a second writer for the current branch."""
    init_git_project(tmp_path)
    first = subprocess.run(
        [
            "python3",
            str(BRANCH_LEASE),
            "--project-dir",
            str(tmp_path),
            "acquire",
            "--branch",
            "feature/phase2",
            "--owner",
            "writer-a",
            "--session-id",
            "session-a",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert first.returncode == 0, first.stderr

    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "COS_SKIP_GOVERNED_INVENTORY": "1",
    }
    second = subprocess.run(
        [
            str(GOVERNED_AGENT),
            "--task-id",
            "phase2-writer-b",
            "--scope",
            "phase2 wiring",
            "--agent-id",
            "writer-b",
            "--session-id",
            "session-b",
            "--",
            "python3",
            "-c",
            "print('would mutate')",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert second.returncode == 2
    assert "BRANCH WRITER LEASE BLOCK" in second.stderr
    assert "writer-a" in second.stderr
    assert "would mutate" not in second.stdout


def test_governed_agent_no_command_claim_only_does_not_take_branch_lease(tmp_path: Path) -> None:
    """Claim-only use releases immediately and does not fight existing branch leases."""
    init_git_project(tmp_path)
    held = subprocess.run(
        [
            "python3",
            str(BRANCH_LEASE),
            "--project-dir",
            str(tmp_path),
            "acquire",
            "--branch",
            "feature/phase2",
            "--owner",
            "writer-a",
            "--session-id",
            "session-a",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert held.returncode == 0, held.stderr

    result = subprocess.run(
        [
            str(GOVERNED_AGENT),
            "--task-id",
            "claim-only",
            "--scope",
            "read-only planning",
            "--agent-id",
            "reader-b",
            "--session-id",
            "session-b",
        ],
        cwd=tmp_path,
        env={**os.environ, "COGNITIVE_OS_PROJECT_DIR": str(tmp_path), "COS_SKIP_GOVERNED_INVENTORY": "1"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "claim acquired; no command supplied" in result.stderr


def test_run_task_safe_mode_blocks_admission_without_deleting_artifacts(tmp_path: Path) -> None:
    """Safe mode blocks new admission and preserves prior task evidence."""
    existing = tmp_path / ".cognitive-os" / "headless" / "tasks" / "existing.json"
    existing.parent.mkdir(parents=True)
    existing.write_text('{"status":"kept"}\n', encoding="utf-8")

    enabled = subprocess.run(
        ["python3", str(SAFE_MODE), "enable", "--project-dir", str(tmp_path), "--reason", "incident", "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert enabled.returncode == 0, enabled.stderr

    result = subprocess.run(
        ["python3", str(RUN_TASK), "--project-dir", str(tmp_path), "--task-id", "blocked-task", "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    data = json_payload(result)
    assert result.returncode == 2
    assert data["status"] == "blocked"
    assert data["safe_mode"]["safe_mode"] is True  # type: ignore[index]
    assert existing.read_text(encoding="utf-8") == '{"status":"kept"}\n'
    assert not (tmp_path / ".cognitive-os" / "headless" / "tasks" / "blocked-task.json").exists()


def test_run_task_malformed_safe_mode_fails_closed(tmp_path: Path) -> None:
    state = tmp_path / ".cognitive-os" / "runtime" / "headless-safe-mode.json"
    state.parent.mkdir(parents=True)
    state.write_text("{not-json", encoding="utf-8")

    result = subprocess.run(
        ["python3", str(RUN_TASK), "--project-dir", str(tmp_path), "--task-id", "malformed-state", "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    data = json_payload(result)
    assert result.returncode == 2
    assert data["status"] == "blocked"
    assert "unreadable" in str(data["reason"])
    assert not (tmp_path / ".cognitive-os" / "headless" / "tasks" / "malformed-state.json").exists()


def test_run_task_blocks_headless_direct_main_publication_before_success_artifact(tmp_path: Path) -> None:
    """Publication args are checked by the protected-publication primitive."""
    init_git_project(tmp_path, branch="feature/repair")

    result = subprocess.run(
        [
            "python3",
            str(RUN_TASK),
            "--project-dir",
            str(tmp_path),
            "--task-id",
            "publish-main",
            "--actor-mode",
            "headless",
            "--publication-target",
            "main",
            "--landing-mode",
            "none",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    data = json_payload(result)
    assert result.returncode == 2
    assert data["status"] == "blocked"
    assert data["publication"]["decision"] == "block"  # type: ignore[index]
    assert not (tmp_path / ".cognitive-os" / "headless" / "tasks" / "publish-main.json").exists()


def test_run_task_wrapper_has_valid_bash_syntax() -> None:
    result = subprocess.run(["bash", "-n", str(RUN_TASK_WRAPPER)], text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
