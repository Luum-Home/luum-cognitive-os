"""Live ADR-098 edit-lock conflict exercise.

This covers the previously unproven Phase B/C behavior with a real holder
process: PreToolUse blocks a second session while the first session's lock PID is
alive, and Stop/session-end releases that lock so the second session can proceed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _install_lock_layer(fake_project: Path) -> None:
    """Copy the lock primitive and hooks into a fake COS project."""
    (fake_project / ".claude").mkdir(parents=True)
    (fake_project / "scripts").mkdir()
    (fake_project / "hooks").mkdir()
    for src, dst in [
        (REPO_ROOT / "scripts" / "edit-coop.sh", fake_project / "scripts" / "edit-coop.sh"),
        (REPO_ROOT / "hooks" / "edit-lock-pre-tool.sh", fake_project / "hooks" / "edit-lock-pre-tool.sh"),
        (REPO_ROOT / "hooks" / "edit-lock-session-end.sh", fake_project / "hooks" / "edit-lock-session-end.sh"),
    ]:
        shutil.copy2(src, dst)
        dst.chmod(0o755)


def _env(fake_project: Path, session_id: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(fake_project),
            "COGNITIVE_OS_PROJECT_DIR": str(fake_project),
            "COGNITIVE_OS_SESSION_ID": session_id,
            "COS_AGENT_ID": session_id,
            "COS_EDIT_LOCK_TTL": "60",
        }
    )
    env.pop("COS_EDIT_LOCK_NO_PID_CHECK", None)
    env.pop("COS_BYPASS_EDIT_LOCK", None)
    return env


def _run_pre_tool(fake_project: Path, session_id: str, file_path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(fake_project / "hooks" / "edit-lock-pre-tool.sh")],
        input=json.dumps({"tool_input": {"file_path": file_path}}),
        env=_env(fake_project, session_id),
        cwd=fake_project,
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.mark.integration
def test_live_conflict_blocks_then_session_end_releases(tmp_path: Path) -> None:
    """A live session-A lock blocks session-B until session-A Stop releases it."""
    fake_project = tmp_path / "cos-project"
    _install_lock_layer(fake_project)
    target = "docs/shared-contract.md"
    lock_meta = fake_project / ".cognitive-os" / "runtime" / "edit-locks" / "docs--shared-contract.md" / "meta.yaml"

    holder = subprocess.Popen(["sleep", "60"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    lock_meta.parent.mkdir(parents=True, exist_ok=True)
    lock_meta.write_text(
        f'''session_id: "session-A"
agent_id: "session-A"
agent_role: "orchestrator"
worktree: "{fake_project}"
pid: {holder.pid}
target_file: "{target}"
intent: "exclusive-edit"
since: "2026-05-01T00:00:00Z"
heartbeat: "2099-01-01T00:00:00Z"
expires_at: "2099-01-01T00:01:00Z"
purpose: "live-conflict-test"
related_adr: "ADR-098"
related_files: []
allows_concurrent_read: true
on_conflict_other_agent_should: "park"
status: "active"
'''
    )
    try:
        deadline = time.time() + 10
        while time.time() < deadline and not lock_meta.exists():
            if holder.poll() is not None:
                _, stderr = holder.communicate(timeout=1)
                pytest.fail(f"holder exited before acquiring lock: {stderr}")
            time.sleep(0.05)
        assert lock_meta.exists(), "session-A should hold a live edit lock"

        blocked = _run_pre_tool(fake_project, "session-B", target)
        assert blocked.returncode == 2
        assert "EDIT-LOCK CONFLICT" in blocked.stderr
        assert "session=session-A" in blocked.stderr

        released = subprocess.run(
            ["bash", str(fake_project / "hooks" / "edit-lock-session-end.sh")],
            env=_env(fake_project, "session-A"),
            cwd=fake_project,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert released.returncode == 0, released.stderr
        assert not lock_meta.exists(), "session-end must release session-A locks"

        allowed = _run_pre_tool(fake_project, "session-B", target)
        assert allowed.returncode == 0, allowed.stderr
        assert lock_meta.exists(), "session-B should acquire after session-A releases"
        assert 'session_id: "session-B"' in lock_meta.read_text()
    finally:
        holder.terminate()
        try:
            holder.wait(timeout=2)
        except subprocess.TimeoutExpired:
            holder.kill()
            holder.wait(timeout=2)
