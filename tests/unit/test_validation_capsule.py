"""Tests for validation capsule isolation and concurrent-agent suppression."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parents[1].parent
CAPSULE = PROJECT_ROOT / "scripts" / "cos-validation-capsule.sh"
PRE_AGENT_SNAPSHOT = PROJECT_ROOT / "hooks" / "pre-agent-snapshot.sh"
PROFILE_AUTOAPPLY = PROJECT_ROOT / "hooks" / "profile-drift-autoapply.sh"


def test_validation_capsule_runs_in_isolated_worktree_and_exports_guards() -> None:
    result = subprocess.run(
        [
            "bash",
            str(CAPSULE),
            "--allow-dirty",
            "--name",
            "unit-guards",
            "--",
            "bash",
            "-c",
            "pwd; test \"$COS_VALIDATION_MODE\" = 1 && test \"$COS_SUPPRESS_AGENT_SNAPSHOT\" = 1 && test \"$COS_DISABLE_PROFILE_AUTOAPPLY\" = 1",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    capsule_pwd = result.stdout.strip().splitlines()[0]
    assert str(PROJECT_ROOT) not in capsule_pwd
    assert "cos-validation-capsules" in capsule_pwd
    assert not (PROJECT_ROOT / ".cognitive-os" / "runtime" / "validation-capsule.lock").exists()


def test_validation_lock_helper_treats_live_lock_as_active(tmp_path: Path) -> None:
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "validation-capsule.lock").write_text(
        json.dumps(
            {
                "run_id": "unit",
                "pid": os.getpid(),
                "expires_at_epoch": int(time.time()) + 120,
                "message": "unit validation",
            }
        )
        + "\n"
    )
    result = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{PROJECT_ROOT}/hooks/_lib/validation-lock.sh"; cos_validation_lock_active "{tmp_path}"',
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_dispatch_gate_blocks_agent_launch_during_validation_capsule(tmp_path: Path) -> None:
    runtime = tmp_path / ".cognitive-os" / "runtime"
    metrics = tmp_path / ".cognitive-os" / "metrics"
    runtime.mkdir(parents=True)
    metrics.mkdir(parents=True)
    (runtime / "validation-capsule.lock").write_text(
        json.dumps(
            {
                "run_id": "unit",
                "pid": os.getpid(),
                "expires_at_epoch": int(time.time()) + 120,
                "message": "unit validation lock",
            }
        )
        + "\n"
    )
    payload = {"tool_name": "Agent", "tool_input": {"prompt": "change files"}}
    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "hooks" / "dispatch-gate.sh")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "COS_VALIDATION_ALLOW_CONCURRENT_AGENTS": "0",
        },
        timeout=5,
    )
    assert result.returncode == 2
    assert "validation capsule active" in result.stderr


def test_pre_agent_snapshot_suppression_does_not_stash_dirty_work(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    tracked = repo / "tracked.txt"
    tracked.write_text("base\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, capture_output=True)
    tracked.write_text("dirty\n")

    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(repo),
        "COS_SUPPRESS_AGENT_SNAPSHOT": "1",
        "COGNITIVE_OS_SESSION_ID": "unit-validation",
    }
    result = subprocess.run(
        ["bash", str(PRE_AGENT_SNAPSHOT)],
        cwd=repo,
        env=env,
        input='{"tool_name":"Agent","tool_input":{"description":"unit"}}',
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert tracked.read_text() == "dirty\n"
    stash = subprocess.run(["git", "stash", "list"], cwd=repo, text=True, capture_output=True, check=True)
    assert "auto-pre-agent" not in stash.stdout


def test_profile_autoapply_respects_validation_mode() -> None:
    content = PROFILE_AUTOAPPLY.read_text()
    assert "cos_validation_lock_active" in content
    assert "COS_DISABLE_PROFILE_AUTOAPPLY" in content
