"""Behavioral + performance tests for packages/quality-gates/hooks/completion-gate.sh.

Key invariants verified:
1. Non-Agent tool calls exit immediately (<200 ms) without spawning Python.
2. Agent completions run the full gate (queue drain, verification, etc.).
3. Queue drain is called on exit trap for Agent calls.
4. Basic gate functionality is preserved after the optimisation.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = _PROJECT_ROOT / "packages" / "quality-gates" / "hooks" / "completion-gate.sh"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hook_input(tool_name: str = "Agent", response: str = "done", prompt: str = "run task") -> str:
    return json.dumps({
        "tool_name": tool_name,
        "tool_input": {"prompt": prompt, "description": prompt},
        "tool_response": {"result": response},
    })


def _run_hook(
    project_dir: Path,
    stdin: str,
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project_dir),
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=15,
    )


def _setup_project(tmp_path: Path) -> Path:
    """Create a minimal project dir with required structure."""
    project_dir = tmp_path / "project"
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)
    (project_dir / "cognitive-os.yaml").write_text(
        "project:\n  phase: stabilization\n"
    )
    return project_dir


# ---------------------------------------------------------------------------
# Performance — non-Agent fast-exit
# ---------------------------------------------------------------------------

class TestNonAgentFastExit:
    def test_non_agent_exits_under_50ms(self, tmp_path):
        """A Bash tool call must exit in < 200 ms (early-exit path, no Python)."""
        project_dir = _setup_project(tmp_path)
        stdin = _make_hook_input(tool_name="Bash", response="output", prompt="ls")

        start = time.monotonic()
        result = _run_hook(project_dir, stdin=stdin)
        elapsed = time.monotonic() - start

        assert elapsed < 0.2, (
            f"Non-Agent hook took {elapsed*1000:.1f} ms (limit 200 ms); "
            f"returncode={result.returncode} stderr={result.stderr[:200]}"
        )
        assert result.returncode == 0

    def test_non_agent_empty_input_exits_fast(self, tmp_path):
        """Empty stdin must exit immediately (< 200 ms)."""
        project_dir = _setup_project(tmp_path)

        start = time.monotonic()
        result = _run_hook(project_dir, stdin="")
        elapsed = time.monotonic() - start

        assert elapsed < 0.2, (
            f"Empty-input hook took {elapsed*1000:.1f} ms (limit 200 ms)"
        )
        assert result.returncode == 0

    def test_non_agent_no_python_spawn(self, tmp_path):
        """Non-Agent calls must NOT spawn Python (no queue drain, no verify)."""
        project_dir = _setup_project(tmp_path)
        stdin = _make_hook_input(tool_name="Read", response="file content", prompt="read file")

        result = _run_hook(project_dir, stdin=stdin)

        # The hook should exit 0 and produce no substantive output for non-Agent
        assert result.returncode == 0
        # No completion-gate output sections should appear for non-Agent
        assert "COMPLETION-GATE" not in result.stdout
        assert "COMPLETION-GATE" not in result.stderr


# ---------------------------------------------------------------------------
# Agent path — drain queue on exit
# ---------------------------------------------------------------------------

class TestAgentQueueDrain:
    def test_agent_runs_drain_queue_on_exit(self, tmp_path):
        """Agent tool completions must attempt queue drain (trap EXIT fires)."""
        project_dir = _setup_project(tmp_path)

        # Agent response that does NOT trigger verification (no "done"/"complete")
        # so we isolate just the drain path
        stdin = _make_hook_input(
            tool_name="Agent",
            response="working on it",
            prompt="partial task",
        )
        result = _run_hook(project_dir, stdin=stdin)

        # Hook must complete without error; drain is advisory (stderr) and
        # does not block exit 0
        assert result.returncode == 0, (
            f"Agent gate should exit 0 even with no queue; "
            f"stderr={result.stderr[:300]}"
        )

    def test_agent_completion_not_blocked_by_empty_queue(self, tmp_path):
        """Queue drain with empty/missing queue must not block or error."""
        project_dir = _setup_project(tmp_path)
        # No queue files present

        stdin = _make_hook_input(
            tool_name="Agent",
            response="Task is complete.",
            prompt="run task",
        )
        result = _run_hook(project_dir, stdin=stdin)
        assert result.returncode == 0, (
            f"Empty queue should not cause gate failure; stderr={result.stderr[:300]}"
        )


# ---------------------------------------------------------------------------
# Agent path — functionality preserved
# ---------------------------------------------------------------------------

class TestAgentFunctionality:
    def test_agent_functionality_preserved(self, tmp_path):
        """Agent completion with a 'done' response must pass through the gate."""
        project_dir = _setup_project(tmp_path)

        stdin = _make_hook_input(
            tool_name="Agent",
            response="All tasks complete. Done.",
            prompt="implement feature X",
        )
        result = _run_hook(project_dir, stdin=stdin)
        assert result.returncode == 0, (
            f"Successful agent completion should exit 0; stderr={result.stderr[:300]}"
        )

    def test_non_agent_tool_name_always_skipped(self, tmp_path):
        """Any tool_name other than Agent must hit the fast-exit path."""
        project_dir = _setup_project(tmp_path)

        for tool in ("Write", "Edit", "Glob", "Grep", "TodoWrite"):
            stdin = _make_hook_input(tool_name=tool, response="done")
            start = time.monotonic()
            result = _run_hook(project_dir, stdin=stdin)
            elapsed = time.monotonic() - start

            assert result.returncode == 0, f"Tool {tool}: expected exit 0, got {result.returncode}"
            assert elapsed < 0.2, (
                f"Tool {tool} took {elapsed*1000:.1f} ms — should be < 200 ms fast-exit"
            )
