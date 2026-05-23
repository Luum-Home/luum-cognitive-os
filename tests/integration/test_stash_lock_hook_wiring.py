from __future__ import annotations

import os
import json
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]


def _git(project: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=project,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _scratch_repo(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    _git(project, "init")
    _git(project, "config", "user.email", "stash-lock@example.invalid")
    _git(project, "config", "user.name", "Stash Lock Test")
    (project / "tracked.txt").write_text("initial\n", encoding="utf-8")
    _git(project, "add", "tracked.txt")
    _git(project, "commit", "-m", "baseline")
    return project


def _hold_stash_lock(project: Path) -> subprocess.Popen[str]:
    script = (
        f"export COGNITIVE_OS_PROJECT_DIR={project!s}; "
        f"source {ROOT / 'hooks/_lib/stash-lock.sh'}; "
        "cos_stash_lock_acquire test-holder || exit 1; "
        "sleep 8"
    )
    proc = subprocess.Popen(
        ["bash", "-lc", script],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    lock_file = project / ".cognitive-os" / "runtime" / "stash.lock"
    deadline = time.time() + 3
    while time.time() < deadline:
        if lock_file.exists():
            return proc
        if proc.poll() is not None:
            out, err = proc.communicate(timeout=1)
            raise AssertionError(f"lock holder exited early: stdout={out} stderr={err}")
        time.sleep(0.05)
    proc.terminate()
    raise AssertionError("lock holder did not acquire stash lock")


@pytest.mark.parametrize(
    "hook",
    [
        "hooks/auto-checkpoint.sh",
        "hooks/pre-agent-snapshot.sh",
        "hooks/post-agent-snapshot-restore.sh",
    ],
)
def test_stash_mutating_hooks_source_stash_lock(hook: str) -> None:
    text = (ROOT / hook).read_text(encoding="utf-8")

    assert "_lib/stash-lock.sh" in text


@pytest.mark.parametrize(
    "hook",
    [
        "hooks/auto-checkpoint.sh",
        "hooks/pre-agent-snapshot.sh",
        "hooks/post-agent-snapshot-restore.sh",
    ],
)
def test_stash_mutating_hooks_acquire_and_release_lock(hook: str) -> None:
    text = (ROOT / hook).read_text(encoding="utf-8")

    assert "cos_stash_lock_acquire" in text
    assert "cos_stash_lock_release" in text


def test_auto_checkpoint_respects_held_stash_lock(tmp_path: Path) -> None:
    project = _scratch_repo(tmp_path)
    (project / "tracked.txt").write_text("dirty change\n", encoding="utf-8")
    checkpoint_dir = project / ".cognitive-os" / "checkpoints"
    checkpoint_dir.mkdir(parents=True)
    (checkpoint_dir / ".last-checkpoint").write_text("0", encoding="utf-8")

    holder = _hold_stash_lock(project)
    try:
        env = os.environ.copy()
        env.update(
            {
                "CLAUDE_PROJECT_DIR": str(project),
                "COGNITIVE_OS_PROJECT_DIR": str(project),
                "COS_ALLOW_DESTRUCTIVE_GIT": "1",
                "COS_AUTO_CHECKPOINT_USE_STASH": "1",
                "COS_STASH_LOCK_TIMEOUT": "1",
                "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
            }
        )
        result = subprocess.run(
            ["bash", str(ROOT / "hooks/auto-checkpoint.sh")],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=5,
            check=False,
        )
    finally:
        holder.terminate()
        try:
            holder.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            holder.kill()

    assert result.returncode == 0, result.stderr
    assert "could not acquire stash lock" in result.stderr
    checkpoints = list(checkpoint_dir.glob("cos-*.json"))
    assert len(checkpoints) == 1
    metadata = json.loads(checkpoints[0].read_text(encoding="utf-8"))
    assert metadata["stash_name"] == "copy-only-lock-failed"
    assert metadata["copied_files"] == ["tracked.txt"]
    assert (project / "tracked.txt").read_text(encoding="utf-8") == "dirty change\n"
