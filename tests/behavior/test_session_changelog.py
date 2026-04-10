"""Behavior tests for session-changelog.sh Stop hook."""

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior


def _init_git_with_commit(project_dir: Path):
    """Configure git identity and make an initial commit."""
    subprocess.run(["git", "config", "user.email", "test@example.com"],
                   cwd=str(project_dir), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"],
                   cwd=str(project_dir), capture_output=True)
    readme = project_dir / "README.md"
    readme.write_text("# test")
    subprocess.run(["git", "add", str(readme)], cwd=str(project_dir), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(project_dir), capture_output=True)


class TestSessionChangelog:

    def _setup_session(self, cognitive_os_env, tasks=None, decisions=None):
        """Create meta.json, active-tasks.json, and optionally a git repo."""
        project_dir = cognitive_os_env["project_dir"]
        session_id = cognitive_os_env["session_id"]
        cos_dir = cognitive_os_env["cos_dir"]

        _init_git_with_commit(project_dir)

        session_dir = cos_dir / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "session_id": session_id,
            "start_time": "2026-04-10T10:00:00Z",
            "date": "2026-04-10",
            "decisions": decisions or [],
        }
        (session_dir / "meta.json").write_text(json.dumps(meta))

        # active-tasks.json
        tasks_dir = cos_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        task_list = tasks or [
            {
                "id": "task-1",
                "description": "feat: implement feature X",
                "status": "completed",
                "session_id": session_id,
            }
        ]
        (tasks_dir / "active-tasks.json").write_text(json.dumps({"tasks": task_list}))

    def test_generates_changelog_file(self, run_hook, cognitive_os_env):
        """G1: Hook generates .cognitive-os/changelogs/{session_id}.md."""
        session_id = cognitive_os_env["session_id"]
        cos_dir = cognitive_os_env["cos_dir"]

        self._setup_session(cognitive_os_env)

        result = run_hook(
            "session-changelog.sh",
            env=cognitive_os_env["env"],
            stdin="",
        )

        assert result.returncode == 0, f"Hook failed: {result.stderr}"

        changelog_file = cos_dir / "changelogs" / f"{session_id}.md"
        assert changelog_file.exists(), "changelog file was not created"

        content = changelog_file.read_text()
        assert "Session Changelog" in content, "Missing 'Session Changelog' in output"
        assert "Tasks Completed" in content, "Missing 'Tasks Completed' in output"

    def test_appends_to_sprint_changelog(self, run_hook, cognitive_os_env):
        """G2: When sprint-status.yaml exists, appends to sprint-{id}.md."""
        session_id = cognitive_os_env["session_id"]
        cos_dir = cognitive_os_env["cos_dir"]

        self._setup_session(cognitive_os_env)

        # Create sprint-status.yaml
        state_dir = cos_dir / "workflows" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        sprint_yaml = state_dir / "sprint-status.yaml"
        sprint_yaml.write_text('sprint_id: "2026-w15"\nstatus: active\n')

        result = run_hook(
            "session-changelog.sh",
            env=cognitive_os_env["env"],
            stdin="",
        )

        assert result.returncode == 0, f"Hook failed: {result.stderr}"

        # Session changelog must exist
        session_changelog = cos_dir / "changelogs" / f"{session_id}.md"
        assert session_changelog.exists()

        # Sprint changelog must also exist
        sprint_changelog = cos_dir / "changelogs" / "sprint-2026-w15.md"
        assert sprint_changelog.exists(), "sprint changelog was not created"

        sprint_content = sprint_changelog.read_text()
        assert "2026-w15" in sprint_content or session_id in sprint_content

    def test_exits_zero_without_session_id(self, run_hook, cognitive_os_env):
        """Hook exits 0 when SESSION_ID is not set."""
        env = cognitive_os_env["env"].copy()
        env["COGNITIVE_OS_SESSION_ID"] = ""

        result = run_hook("session-changelog.sh", env=env, stdin="")
        assert result.returncode == 0

    def test_creates_changelogs_dir_if_missing(self, run_hook, cognitive_os_env):
        """Hook creates the changelogs directory if it does not exist."""
        cos_dir = cognitive_os_env["cos_dir"]
        changelogs_dir = cos_dir / "changelogs"

        # Ensure it does not exist
        import shutil
        if changelogs_dir.exists():
            shutil.rmtree(changelogs_dir)

        self._setup_session(cognitive_os_env)

        result = run_hook(
            "session-changelog.sh",
            env=cognitive_os_env["env"],
            stdin="",
        )

        assert result.returncode == 0
        assert changelogs_dir.exists(), "changelogs dir was not created"

    def test_no_sprint_file_no_sprint_changelog(self, run_hook, cognitive_os_env):
        """Without sprint-status.yaml, no sprint changelog file is created."""
        cos_dir = cognitive_os_env["cos_dir"]

        self._setup_session(cognitive_os_env)

        # Ensure sprint file is absent
        sprint_file = cos_dir / "workflows" / "state" / "sprint-status.yaml"
        sprint_file.unlink(missing_ok=True)

        result = run_hook(
            "session-changelog.sh",
            env=cognitive_os_env["env"],
            stdin="",
        )

        assert result.returncode == 0

        # No sprint changelog files should be created
        changelogs_dir = cos_dir / "changelogs"
        sprint_files = list(changelogs_dir.glob("sprint-*.md")) if changelogs_dir.exists() else []
        assert len(sprint_files) == 0, f"Unexpected sprint changelog files: {sprint_files}"
