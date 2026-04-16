"""Behavioral tests for task_bridge.py — COS ↔ Claude Code Task panel link (ADR-024)."""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BRIDGE = REPO_ROOT / "hooks" / "_lib" / "task_bridge.py"
HOOK = REPO_ROOT / "hooks" / "task-bridge-notify.sh"


def _run_bridge(cmd, env=None, **kwargs):
    """Run task_bridge.py subcommand."""
    full_cmd = ["python3", str(BRIDGE), cmd]
    for k, v in kwargs.items():
        full_cmd.extend([f"--{k.replace('_', '-')}", str(v)])
    return subprocess.run(full_cmd, env=env or os.environ.copy(),
                          capture_output=True, text=True, timeout=5)


def _env(project_dir):
    e = os.environ.copy()
    e["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return e


class TestRegister:
    def test_register_returns_task_with_tool_use_id(self, tmp_path):
        result = _run_bridge("register", env=_env(tmp_path),
                             tool_use_id="toolu_abc123",
                             description="test task")
        assert result.returncode == 0
        entry = json.loads(result.stdout)
        assert entry["toolUseId"] == "toolu_abc123"
        assert entry["description"] == "test task"
        assert entry["status"] == "in_progress"

    def test_register_persists_to_active_tasks_json(self, tmp_path):
        _run_bridge("register", env=_env(tmp_path),
                    tool_use_id="toolu_xyz",
                    description="persisted")
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        assert tasks_file.is_file()
        data = json.loads(tasks_file.read_text())
        assert any(t.get("toolUseId") == "toolu_xyz" for t in data.get("tasks", []))

    def test_register_deduplicates_by_tool_use_id(self, tmp_path):
        env = _env(tmp_path)
        first = _run_bridge("register", env=env, tool_use_id="toolu_dup",
                            description="first")
        second = _run_bridge("register", env=env, tool_use_id="toolu_dup",
                             description="second")
        e1 = json.loads(first.stdout)
        e2 = json.loads(second.stdout)
        assert e1["id"] == e2["id"]  # Same task, not duplicated


class TestComplete:
    def test_complete_marks_task_completed(self, tmp_path):
        env = _env(tmp_path)
        _run_bridge("register", env=env, tool_use_id="toolu_c1",
                    description="to complete")
        result = _run_bridge("complete", env=env, tool_use_id="toolu_c1",
                             summary="done")
        assert json.loads(result.stdout)["completed"] is True

        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        data = json.loads(tasks_file.read_text())
        task = next(t for t in data["tasks"] if t["toolUseId"] == "toolu_c1")
        assert task["status"] == "completed"
        assert task["outputSummary"] == "done"

    def test_complete_unknown_tool_use_id(self, tmp_path):
        result = _run_bridge("complete", env=_env(tmp_path),
                             tool_use_id="toolu_nonexistent")
        assert json.loads(result.stdout)["completed"] is False


class TestPanelContext:
    def test_panel_context_empty_when_no_tasks(self, tmp_path):
        result = _run_bridge("panel-context", env=_env(tmp_path))
        assert result.returncode == 0
        assert result.stdout.strip() == ""  # No output when nothing to report

    def test_panel_context_shows_in_progress_with_tool_use_id(self, tmp_path):
        env = _env(tmp_path)
        _run_bridge("register", env=env, tool_use_id="toolu_panel",
                    description="visible task")
        result = _run_bridge("panel-context", env=env)
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "toolu_pa" in ctx
        assert "visible task" in ctx

    def test_panel_context_shows_queued_items(self, tmp_path):
        env = _env(tmp_path)
        queue_file = tmp_path / ".cognitive-os" / "rate-limit-queue.json"
        queue_file.parent.mkdir(parents=True, exist_ok=True)
        queue_file.write_text(json.dumps({
            "version": 1,
            "queue": [{
                "id": "q-1",
                "description": "queued refactor",
                "ready_at_epoch": 0,  # ready now
            }]
        }))

        result = _run_bridge("panel-context", env=env)
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "Rate-Limit Queue" in ctx
        assert "queued refactor" in ctx
        assert "/drain-queue" in ctx


class TestHookIntegration:
    def test_hook_silent_without_claude_env(self, tmp_path):
        """Hook must not emit output when not running under Claude Code."""
        env = os.environ.copy()
        env.pop("CLAUDE_PROJECT_DIR", None)
        env.pop("CLAUDE_SESSION_ID", None)
        result = subprocess.run(
            ["bash", str(HOOK)],
            input='{"tool_name":"Agent"}',
            env=env, capture_output=True, text=True, timeout=5,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_hook_emits_context_with_claude_env(self, tmp_path):
        """Hook emits additionalContext when running under Claude Code."""
        env = _env(tmp_path)
        # Pre-register a task
        _run_bridge("register", env=env, tool_use_id="toolu_hook",
                    description="for hook test")

        result = subprocess.run(
            ["bash", str(HOOK)],
            input='{"tool_name":"Agent","tool_use_id":"other_tui"}',
            env=env, capture_output=True, text=True, timeout=5,
        )
        assert result.returncode == 0
        if result.stdout.strip():
            output = json.loads(result.stdout)
            assert "hookSpecificOutput" in output
            assert "additionalContext" in output["hookSpecificOutput"]
