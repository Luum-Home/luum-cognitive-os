from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EDIT_COOP = REPO_ROOT / "scripts" / "edit-coop.sh"


def run_edit(project: Path, session: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project)
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env["COGNITIVE_OS_SESSION_ID"] = session
    env["COS_EDIT_LOCK_NO_PID_CHECK"] = "1"
    env.pop("COS_BYPASS_EDIT_LOCK", None)
    return subprocess.run(
        ["bash", str(EDIT_COOP), *args],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )


@pytest.fixture
def scratch_repo(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".claude").mkdir()
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project, check=True)
    (project / "target.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "target.txt"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=project, check=True, capture_output=True)
    return project


@pytest.mark.integration
def test_two_agents_editing_same_file_conflict_is_structured_and_non_destructive(scratch_repo: Path):
    target = scratch_repo / "target.txt"

    first = run_edit(scratch_repo, "session-A", ["acquire", "target.txt", "scenario-1", "exclusive-edit"])
    assert first.returncode == 0, first.stderr
    target.write_text("session-A edit\n", encoding="utf-8")

    second = run_edit(scratch_repo, "session-B", ["acquire", "target.txt", "scenario-1", "exclusive-edit"])
    assert second.returncode == 2
    assert "BLOCKED" in second.stderr
    assert "session=session-A" in second.stderr

    check = run_edit(scratch_repo, "session-B", ["check", "target.txt"])
    assert check.returncode == 2
    assert "HELD" in check.stdout
    assert "session=session-A" in check.stdout
    assert "target_file: \"target.txt\"" in check.stdout
    assert "on_conflict_other_agent_should" in check.stdout

    # The blocked writer must not silently clobber the first writer.
    assert target.read_text(encoding="utf-8") == "session-A edit\n"

    released = run_edit(scratch_repo, "session-A", ["release", "target.txt"])
    assert released.returncode == 0, released.stderr
    reacquire = run_edit(scratch_repo, "session-B", ["acquire", "target.txt", "after-release", "exclusive-edit"])
    assert reacquire.returncode == 0, reacquire.stderr
