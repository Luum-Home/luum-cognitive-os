from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COS = PROJECT_ROOT / "scripts" / "cos"


def run_agent_daemon(project: Path, *args: str) -> dict:
    result = subprocess.run(
        [str(COS), "agent", "daemon", "--json", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


@pytest.mark.behavior
def test_cos_agent_daemon_enqueue_list_and_dry_run(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    queued = run_agent_daemon(project, "--project-dir", str(project), "enqueue", "--task-id", "docs", "--command", "echo hi")
    assert queued["status"] == "queued"

    listed = run_agent_daemon(project, "--project-dir", str(project), "list")
    assert [task["task_id"] for task in listed["tasks"]] == ["docs"]

    launched = run_agent_daemon(project, "--project-dir", str(project), "run-once", "--dry-run")
    assert launched["status"] == "launched"
    assert launched["task"]["status"] == "running"


@pytest.mark.behavior
def test_cos_agent_daemon_uses_fake_tmux_runtime(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    fake_tmux = tmp_path / "tmux"
    fake_log = tmp_path / "tmux.log"
    fake_tmux.write_text(
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> {fake_log}\n"
        "exit 0\n"
    )
    fake_tmux.chmod(0o755)

    run_agent_daemon(project, "--project-dir", str(project), "enqueue", "--task-id", "docs", "--command", "echo hi")
    launched = run_agent_daemon(
        project,
        "--project-dir",
        str(project),
        "run-once",
        "--tmux-bin",
        str(fake_tmux),
    )

    assert launched["status"] == "launched"
    assert "new-session -d -s cos-agent-docs" in fake_log.read_text()
