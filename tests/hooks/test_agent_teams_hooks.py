"""Tests for Agent Teams hooks: teammate-idle, task-created, task-completed.

Agent Teams requires an interactive Claude Code session, so the actual event
dispatch cannot be tested in CI. These tests validate that:
  - Each hook parses valid JSON and exits correctly
  - Each hook handles empty stdin gracefully (exit 0)
  - Each hook handles malformed JSON gracefully (exit 0)
  - Phase-aware behavior works (production blocks missing criteria)
  - settings.json registers default events and keeps demoted events opt-in
"""

import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ─── Settings Registration ──────────────────────────────────────────────────


class TestSettingsRegistration:
    """Verify that all Agent Teams events are registered in settings.json."""

    @pytest.fixture(autouse=True)
    def load_settings(self):
        settings_path = PROJECT_ROOT / ".claude" / "settings.json"
        assert settings_path.exists(), ".claude/settings.json not found"
        with open(settings_path) as f:
            self.settings = json.load(f)

    def test_teammate_idle_registered(self):
        assert "TeammateIdle" in self.settings.get("hooks", {}), \
            "TeammateIdle not registered in settings.json"

    def test_task_created_registered(self):
        assert "TaskCreated" in self.settings.get("hooks", {}), \
            "TaskCreated not registered in settings.json"

    def test_task_completed_event_bucket_exists_but_is_demoted(self):
        assert "TaskCompleted" in self.settings.get("hooks", {}), \
            "TaskCompleted not registered in settings.json"
        assert self.settings["hooks"]["TaskCompleted"] == []

    def test_hooks_reference_correct_scripts(self):
        hooks = self.settings["hooks"]
        for event, script in [
            ("TeammateIdle", "teammate-idle.sh"),
            ("TaskCreated", "task-created.sh"),
        ]:
            hook_entries = hooks[event]
            commands = []
            for entry in hook_entries:
                for h in entry.get("hooks", []):
                    commands.append(h.get("command", ""))
            assert any(script in c for c in commands), \
                f"{event} does not reference {script}"


# ─── TeammateIdle Hook ──────────────────────────────────────────────────────


class TestTeammateIdleHook:

    def test_valid_json_no_tasks_file(self, run_hook, mock_project):
        """With valid JSON but no active-tasks.json, exits 0 (allow idle)."""
        result = run_hook(
            "teammate-idle.sh",
            stdin_json={"hook_event_name": "TeammateIdle", "agent_id": "test-1"},
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_valid_json_no_pending_tasks(self, run_hook, mock_project):
        """With tasks file but no pending tasks, exits 0."""
        tasks_dir = mock_project["project_dir"] / ".claude" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        tasks_file = tasks_dir / "active-tasks.json"
        tasks_file.write_text(json.dumps({
            "tasks": [
                {"id": "done-1", "status": "completed", "description": "Already done"}
            ]
        }))

        result = run_hook(
            "teammate-idle.sh",
            stdin_json={"hook_event_name": "TeammateIdle", "agent_id": "test-1"},
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_valid_json_with_pending_tasks(self, run_hook, mock_project):
        """With pending tasks, exits 2 (keep teammate working)."""
        tasks_dir = mock_project["project_dir"] / ".claude" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        tasks_file = tasks_dir / "active-tasks.json"
        tasks_file.write_text(json.dumps({
            "tasks": [
                {"id": "pending-1", "status": "pending", "description": "Implement auth endpoint"}
            ]
        }))

        result = run_hook(
            "teammate-idle.sh",
            stdin_json={"hook_event_name": "TeammateIdle", "agent_id": "test-1"},
            env=mock_project["env"],
        )
        assert result.returncode == 2
        assert "pending task" in result.stdout.lower()

    def test_empty_stdin(self, run_hook, mock_project):
        """Empty stdin should not crash the hook."""
        result = run_hook(
            "teammate-idle.sh",
            stdin_text="",
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_malformed_json(self, run_hook, mock_project):
        """Malformed JSON should not crash the hook."""
        result = run_hook(
            "teammate-idle.sh",
            stdin_text="not json at all {{{",
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_private_mode_skips(self, run_hook, mock_project, private_mode):
        """Private mode causes the hook to exit 0 immediately."""
        result = run_hook(
            "teammate-idle.sh",
            stdin_json={"hook_event_name": "TeammateIdle"},
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_metrics_logged(self, run_hook, mock_project):
        """Hook writes to teammate-idle.jsonl metrics file."""
        result = run_hook(
            "teammate-idle.sh",
            stdin_json={"hook_event_name": "TeammateIdle", "agent_id": "test-1"},
            env=mock_project["env"],
        )
        assert result.returncode == 0

        session_id = mock_project["session_id"]
        metrics_dir = mock_project["cos_dir"] / "sessions" / session_id / "metrics"
        metrics_file = metrics_dir / "teammate-idle.jsonl"
        if metrics_file.exists():
            content = metrics_file.read_text().strip()
            assert len(content) > 0
            entry = json.loads(content.split("\n")[-1])
            assert "timestamp" in entry
            assert "action" in entry


# ─── TaskCreated Hook ───────────────────────────────────────────────────────


class TestTaskCreatedHook:

    def test_valid_task_passes(self, run_hook, mock_project):
        """A task with a good description passes validation."""
        result = run_hook(
            "task-created.sh",
            stdin_json={
                "hook_event_name": "TaskCreated",
                "description": "Implement the user authentication endpoint with JWT",
            },
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_short_description_blocked(self, run_hook, mock_project):
        """A task with a very short description is blocked."""
        result = run_hook(
            "task-created.sh",
            stdin_json={
                "hook_event_name": "TaskCreated",
                "description": "fix bug",
            },
            env=mock_project["env"],
        )
        assert result.returncode == 2
        assert "too short" in result.stdout.lower()

    def test_no_description_field_allows(self, run_hook, mock_project):
        """Missing description field degrades gracefully (allow)."""
        result = run_hook(
            "task-created.sh",
            stdin_json={"hook_event_name": "TaskCreated", "agent_id": "test-1"},
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_production_blocks_missing_criteria(self, run_hook, mock_project):
        """In production phase, tasks without acceptance criteria are blocked."""
        config = mock_project["cos_dir"] / "cognitive-os.yaml"
        config.write_text(
            "project:\n"
            "  name: test-project\n"
            "  phase: production\n"
        )
        root_config = mock_project["project_dir"] / "cognitive-os.yaml"
        root_config.write_text(config.read_text())

        result = run_hook(
            "task-created.sh",
            stdin_json={
                "hook_event_name": "TaskCreated",
                "description": "Add a new REST endpoint for user profiles with response mapping",
            },
            env=mock_project["env"],
        )
        assert result.returncode == 2
        assert "acceptance criteria" in result.stdout.lower()

    def test_production_allows_with_criteria(self, run_hook, mock_project):
        """In production phase, tasks with acceptance criteria pass."""
        config = mock_project["cos_dir"] / "cognitive-os.yaml"
        config.write_text(
            "project:\n"
            "  name: test-project\n"
            "  phase: production\n"
        )
        root_config = mock_project["project_dir"] / "cognitive-os.yaml"
        root_config.write_text(config.read_text())

        result = run_hook(
            "task-created.sh",
            stdin_json={
                "hook_event_name": "TaskCreated",
                "description": "Add user endpoint. Acceptance criteria: tests must pass and coverage > 80%",
            },
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_empty_stdin(self, run_hook, mock_project):
        """Empty stdin should not crash the hook."""
        result = run_hook(
            "task-created.sh",
            stdin_text="",
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_malformed_json(self, run_hook, mock_project):
        """Malformed JSON should not crash the hook."""
        result = run_hook(
            "task-created.sh",
            stdin_text="{{bad json}}",
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_private_mode_skips(self, run_hook, mock_project, private_mode):
        """Private mode causes the hook to exit 0 immediately."""
        result = run_hook(
            "task-created.sh",
            stdin_json={"hook_event_name": "TaskCreated", "description": "x"},
            env=mock_project["env"],
        )
        assert result.returncode == 0


# ─── TaskCompleted Hook ─────────────────────────────────────────────────────


class TestTaskCompletedHook:

    def test_valid_completion_passes(self, run_hook, mock_project):
        """A completion with substantive output passes validation."""
        result = run_hook(
            "task-completed.sh",
            stdin_json={
                "hook_event_name": "TaskCompleted",
                "output": "Implemented the auth endpoint. All tests pass. Coverage at 85%.",
            },
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_short_output_rejected(self, run_hook, mock_project):
        """A completion with trivially short output is rejected."""
        result = run_hook(
            "task-completed.sh",
            stdin_json={
                "hook_event_name": "TaskCompleted",
                "output": "done",
            },
            env=mock_project["env"],
        )
        assert result.returncode == 2
        assert "too short" in result.stdout.lower()

    def test_no_output_field_allows(self, run_hook, mock_project):
        """Missing output field degrades gracefully (allow)."""
        result = run_hook(
            "task-completed.sh",
            stdin_json={"hook_event_name": "TaskCompleted", "task_id": "abc"},
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_production_blocks_missing_trust_report(self, run_hook, mock_project):
        """In production phase, completions without Trust Report are rejected."""
        config = mock_project["cos_dir"] / "cognitive-os.yaml"
        config.write_text(
            "project:\n"
            "  name: test-project\n"
            "  phase: production\n"
        )
        root_config = mock_project["project_dir"] / "cognitive-os.yaml"
        root_config.write_text(config.read_text())

        result = run_hook(
            "task-completed.sh",
            stdin_json={
                "hook_event_name": "TaskCompleted",
                "output": "Implemented the endpoint with full test coverage and documentation updated.",
            },
            env=mock_project["env"],
        )
        assert result.returncode == 2
        assert "trust report" in result.stdout.lower()

    def test_production_allows_with_trust_report(self, run_hook, mock_project):
        """In production phase, completions with Trust Report pass."""
        config = mock_project["cos_dir"] / "cognitive-os.yaml"
        config.write_text(
            "project:\n"
            "  name: test-project\n"
            "  phase: production\n"
        )
        root_config = mock_project["project_dir"] / "cognitive-os.yaml"
        root_config.write_text(config.read_text())

        result = run_hook(
            "task-completed.sh",
            stdin_json={
                "hook_event_name": "TaskCompleted",
                "output": "Implemented endpoint.\nTRUST_REPORT: SCORE=82 STATUS=MEDIUM EVIDENCE=3 UNCERTAINTIES=1\n---\nScore: 82/100",
            },
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_updates_active_tasks(self, run_hook, mock_project):
        """When task_id matches, active-tasks.json is updated."""
        tasks_dir = mock_project["project_dir"] / ".claude" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        tasks_file = tasks_dir / "active-tasks.json"
        tasks_file.write_text(json.dumps({
            "tasks": [
                {"id": "task-42", "status": "in_progress", "description": "Build auth"}
            ]
        }))

        result = run_hook(
            "task-completed.sh",
            stdin_json={
                "hook_event_name": "TaskCompleted",
                "task_id": "task-42",
                "output": "Built the auth endpoint with JWT validation and unit tests.",
            },
            env=mock_project["env"],
        )
        assert result.returncode == 0

        # Verify task was marked completed
        updated = json.loads(tasks_file.read_text())
        task = [t for t in updated["tasks"] if t["id"] == "task-42"][0]
        assert task["status"] == "completed"
        assert "completedAt" in task

    def test_empty_stdin(self, run_hook, mock_project):
        """Empty stdin should not crash the hook."""
        result = run_hook(
            "task-completed.sh",
            stdin_text="",
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_malformed_json(self, run_hook, mock_project):
        """Malformed JSON should not crash the hook."""
        result = run_hook(
            "task-completed.sh",
            stdin_text="not valid json",
            env=mock_project["env"],
        )
        assert result.returncode == 0

    def test_private_mode_skips(self, run_hook, mock_project, private_mode):
        """Private mode causes the hook to exit 0 immediately."""
        result = run_hook(
            "task-completed.sh",
            stdin_json={"hook_event_name": "TaskCompleted", "output": "x"},
            env=mock_project["env"],
        )
        assert result.returncode == 0
