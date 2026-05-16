"""Tests for the Scope Creep Detection system.

Validates that:
- scope-creep-detector.sh hook exists and is valid bash
- Hook skips when no active tasks exist
- Hook skips when task has no scope defined
- Hook detects edits outside the approved scope
- Hook allows edits within scope
- Phase-aware behavior (warn vs block)
- Detections are logged to metrics
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ─── Hook existsnce and syntax ───────────────────────────────────────────────


class TestScopeCreepHook:
    """Tests for hooks/scope-creep-detector.sh."""

    @pytest.fixture
    def hook_path(self):
        return PROJECT_ROOT / "hooks" / "scope-creep-detector.sh"

    def test_hook_exists(self, hook_path):
        """scope-creep-detector.sh must exist."""
        assert hook_path.exists(), f"Missing: {hook_path}"

    def test_hook_is_valid_bash(self, hook_path):
        """Hook must pass bash -n syntax check."""
        result = subprocess.run(
            ["bash", "-n", str(hook_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_hook_is_executable(self, hook_path):
        """Hook must be executable."""
        assert os.access(hook_path, os.X_OK), "Hook is not executable"

    def test_hook_sources_common(self, hook_path):
        """Hook must source _lib/common.sh."""
        content = hook_path.read_text()
        assert '_lib/common.sh' in content, "Hook must source _lib/common.sh"

    def test_hook_checks_private_mode(self, hook_path):
        """Hook must check private mode."""
        content = hook_path.read_text()
        assert "check_private_mode" in content, "Hook must call check_private_mode"

    def test_hook_checks_capability_level(self, hook_path):
        """Hook must respect capability levels."""
        content = hook_path.read_text()
        assert "check_capability_level" in content, (
            "Hook must call check_capability_level"
        )


# ─── Rule file ───────────────────────────────────────────────────────────────


class TestScopeCreepRule:
    """Tests for rules/scope-creep-detection.md."""

    @pytest.fixture
    def rule_path(self):
        return PROJECT_ROOT / "rules" / "scope-creep-detection.md"

    def test_rule_exists(self, rule_path):
        """Rule documentation must exist."""
        assert rule_path.exists(), f"Missing: {rule_path}"

    def test_rule_has_phase_behavior(self, rule_path):
        """Rule must document phase-aware behavior."""
        content = rule_path.read_text()
        assert "Phase Behavior" in content, "Rule must document phase behavior"


# ─── Functional tests ───────────────────────────────────────────────────────


class TestScopeCreepDetection:
    """Functional tests for scope creep detection logic."""

    HOOK_PATH = str(PROJECT_ROOT / "hooks" / "scope-creep-detector.sh")

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure for testing."""
        cos_dir = tmp_path / ".cognitive-os"
        tasks_dir = cos_dir / "tasks"
        metrics_dir = cos_dir / "metrics"
        tasks_dir.mkdir(parents=True)
        metrics_dir.mkdir(parents=True)

        config = tmp_path / "cognitive-os.yaml"
        config.write_text("project:\n  phase: reconstruction\n")

        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        return tmp_path

    def _write_tasks(self, project_dir, tasks):
        """Write active-tasks.json with given tasks."""
        tasks_file = project_dir / ".cognitive-os" / "tasks" / "active-tasks.json"
        tasks_file.write_text(json.dumps({"tasks": tasks}))

    def _run_hook(self, project_dir, file_path, tool_name="Edit"):
        """Run the hook with given parameters."""
        stdin_data = json.dumps({
            "tool_name": tool_name,
            "tool_input": {"file_path": file_path},
        })
        return subprocess.run(
            ["bash", self.HOOK_PATH],
            input=stdin_data,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
                "CODEX_PROJECT_DIR": "",
                "CLAUDE_PROJECT_DIR": str(project_dir),
                "PATH": os.environ.get("PATH", ""),
            },
        )

    def test_skips_when_no_active_tasks_file(self, temp_project):
        """Hook exits 0 when active-tasks.json does not exist."""
        result = self._run_hook(temp_project, "/some/file.go")
        assert result.returncode == 0
        assert "SCOPE CREEP" not in result.stderr

    def test_skips_when_task_has_no_scope(self, temp_project):
        """Hook exits 0 when active task has no scope fields."""
        self._write_tasks(temp_project, [
            {"id": "task-1", "status": "in_progress", "description": "Fix bug"},
        ])
        result = self._run_hook(temp_project, "/some/file.go")
        assert result.returncode == 0
        assert "SCOPE CREEP" not in result.stderr

    def test_allows_edit_within_scope(self, temp_project):
        """Hook exits 0 when edited file is within scope."""
        self._write_tasks(temp_project, [{
            "id": "task-1",
            "status": "in_progress",
            "description": "Implement user handler",
            "scope": ["internal/users/"],
            "expectedFiles": ["internal/users/handler.go"],
        }])
        result = self._run_hook(temp_project, "internal/users/handler.go")
        assert result.returncode == 0
        assert "SCOPE CREEP" not in result.stderr

    def test_scope_prefix_match(self, temp_project):
        """Files under a scope directory should be allowed."""
        self._write_tasks(temp_project, [{
            "id": "task-1",
            "status": "in_progress",
            "description": "Work on users",
            "scope": ["internal/users/"],
        }])
        result = self._run_hook(temp_project, "internal/users/deep/nested/file.go")
        assert result.returncode == 0
        assert "SCOPE CREEP" not in result.stderr

    def test_detects_edit_outside_scope_reconstruction(self, temp_project):
        """Hook warns (exit 0) when file is outside scope in reconstruction."""
        self._write_tasks(temp_project, [{
            "id": "task-1",
            "status": "in_progress",
            "description": "Implement user handler",
            "scope": ["internal/users/"],
        }])
        result = self._run_hook(temp_project, "internal/payments/handler.go")
        assert result.returncode == 0
        assert "SCOPE CREEP: WARNING" in result.stderr

    def test_blocks_edit_outside_scope_production(self, temp_project):
        """Hook blocks (exit 2) when file is outside scope in production."""
        config = temp_project / "cognitive-os.yaml"
        config.write_text("project:\n  phase: production\n")

        self._write_tasks(temp_project, [{
            "id": "task-1",
            "status": "in_progress",
            "description": "Fix user bug",
            "scope": ["internal/users/"],
        }])
        result = self._run_hook(temp_project, "internal/payments/handler.go")
        assert result.returncode == 2
        assert "SCOPE CREEP: BLOCK" in result.stderr

    def test_blocks_edit_outside_scope_maintenance(self, temp_project):
        """Hook blocks (exit 2) in maintenance phase."""
        config = temp_project / "cognitive-os.yaml"
        config.write_text("project:\n  phase: maintenance\n")

        self._write_tasks(temp_project, [{
            "id": "task-1",
            "status": "in_progress",
            "description": "Fix user bug",
            "expectedFiles": ["internal/users/handler.go"],
        }])
        result = self._run_hook(temp_project, "internal/payments/handler.go")
        assert result.returncode == 2

    def test_logs_detection_to_metrics(self, temp_project):
        """Hook logs scope creep detections to metrics JSONL."""
        self._write_tasks(temp_project, [{
            "id": "task-1",
            "status": "in_progress",
            "description": "Implement user handler",
            "scope": ["internal/users/"],
        }])
        self._run_hook(temp_project, "internal/payments/handler.go")

        metrics_file = temp_project / ".cognitive-os" / "metrics" / "scope-creep.jsonl"
        assert metrics_file.exists(), "Metrics file should be created on detection"
        content = metrics_file.read_text().strip()
        entry = json.loads(content)
        assert entry["file"] == "internal/payments/handler.go"
        assert entry["action"] == "warn"

    def test_skips_non_edit_write_tools(self, temp_project):
        """Hook skips for non-Edit/Write tools."""
        self._write_tasks(temp_project, [{
            "id": "task-1",
            "status": "in_progress",
            "scope": ["internal/users/"],
        }])
        result = self._run_hook(
            temp_project, "internal/payments/handler.go", tool_name="Read"
        )
        assert result.returncode == 0
        assert "SCOPE CREEP" not in result.stderr
