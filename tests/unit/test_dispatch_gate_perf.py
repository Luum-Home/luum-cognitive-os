"""Behavioral + performance tests for hooks/dispatch-gate.sh.

Verifies: slot counting, YAML config reading, max-parallel blocking,
model advice emission, and performance after the single-pass Python
dispatch_gate_check.py consolidation.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from tests.unit._helpers import assert_within_absolute

pytestmark = [
    pytest.mark.unit,
    # Perf-budget tests measure latency — incompatible with -n auto CPU contention.
    # cos-test cluster --lane unit excludes 'benchmark' by default; opt-in via
    # cos-test cluster --lane unit -m "unit and benchmark" or COS_RUN_BENCHMARK=1.
    pytest.mark.benchmark,
    # Pin to same worker as test_cos_yaml_readers to coordinate dispatch_gate_check.py
    # subprocess startup cost.
    pytest.mark.xdist_group("dispatch_gate_check_subprocess"),
]

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = _PROJECT_ROOT / "hooks" / "dispatch-gate.sh"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AGENT_STDIN = json.dumps({
    "tool_name": "Agent",
    "tool_input": {
        "prompt": "do some work",
        "description": "do some work",
    },
})


def _run_hook(
    project_dir: Path,
    stdin: str = _AGENT_STDIN,
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "TOOL_NAME": "Agent",
        # Prevent private-mode short-circuit
        "_PRIVATE_MODE_SKIP": "1",
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=10,
    )


def _write_active_tasks(tasks_dir: Path, in_progress: int, completed: int = 0) -> None:
    tasks_dir.mkdir(parents=True, exist_ok=True)
    tasks = []
    for i in range(in_progress):
        tasks.append({"id": f"t{i}", "status": "in_progress", "description": f"task {i}"})
    for i in range(completed):
        tasks.append({"id": f"c{i}", "status": "completed", "description": f"done {i}"})
    (tasks_dir / "active-tasks.json").write_text(
        json.dumps({"tasks": tasks, "lastUpdated": "2026-04-15T00:00:00Z"})
    )


def _write_yaml_config(project_dir: Path, max_parallel: int = 5) -> None:
    config = (
        f"project:\n  phase: stabilization\n"
        f"resources:\n  compute:\n    max_parallel_agents: {max_parallel}\n"
    )
    (project_dir / "cognitive-os.yaml").write_text(config)


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

class TestPerformance:
    def test_completes_under_1s(self, tmp_path):
        """dispatch-gate.sh must complete within a reasonable time budget.

        The nominal limit is 1.0s for the single-pass Python consolidation.
        A slack_factor of 2.0 is applied to absorb CI and cold-start overhead
        while still catching genuine O(n) regressions.
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _write_yaml_config(project_dir, max_parallel=5)
        tasks_dir = project_dir / ".cognitive-os" / "tasks"
        _write_active_tasks(tasks_dir, in_progress=2)

        start = time.monotonic()
        _run_hook(project_dir)
        elapsed = time.monotonic() - start

        # 1.0s nominal budget × 2.0 slack = 2.0s effective limit
        assert_within_absolute(elapsed, limit_s=1.0, slack_factor=2.0)


# ---------------------------------------------------------------------------
# Blocking behaviour
# ---------------------------------------------------------------------------

class TestBlocking:
    def test_blocks_at_max_parallel_agents(self, tmp_path):
        """When active tasks >= max_parallel_agents, hook must exit 2 (block)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        max_agents = 3
        _write_yaml_config(project_dir, max_parallel=max_agents)
        tasks_dir = project_dir / ".cognitive-os" / "tasks"
        _write_active_tasks(tasks_dir, in_progress=max_agents)

        result = _run_hook(project_dir)
        assert result.returncode == 2, (
            f"Expected block (exit 2) at {max_agents}/{max_agents} agents; "
            f"got {result.returncode}; stderr={result.stderr[:300]}"
        )
        queue = project_dir / ".cognitive-os" / "tasks" / "dispatch-queue.json"
        queued = json.loads(queue.read_text(encoding="utf-8"))
        assert queued[0]["prompt"] == "do some work"

    def test_blocks_without_queueing_when_agent_payload_missing(self, tmp_path):
        """A blocked Agent launch with unavailable stdin must not persist empty prompt."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _write_yaml_config(project_dir, max_parallel=1)
        tasks_dir = project_dir / ".cognitive-os" / "tasks"
        _write_active_tasks(tasks_dir, in_progress=1)

        result = _run_hook(project_dir, stdin="")

        assert result.returncode == 2
        assert "Could not enqueue" in result.stderr
        assert "missing Agent prompt" in result.stderr
        assert "Agent enqueued" not in result.stderr
        queue = project_dir / ".cognitive-os" / "tasks" / "dispatch-queue.json"
        assert not queue.exists()

    def test_allows_when_below_max(self, tmp_path):
        """When active tasks < max_parallel_agents, hook must allow (exit 0)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _write_yaml_config(project_dir, max_parallel=5)
        tasks_dir = project_dir / ".cognitive-os" / "tasks"
        _write_active_tasks(tasks_dir, in_progress=2)

        result = _run_hook(project_dir)
        assert result.returncode == 0, (
            f"Expected allow (exit 0); got {result.returncode}; stderr={result.stderr[:300]}"
        )


# ---------------------------------------------------------------------------
# Model advice
# ---------------------------------------------------------------------------

class TestModelAdvice:
    def test_emits_model_advice(self, tmp_path):
        """Hook must emit a MODEL_ADVICE or 'Model:' line to stderr on allow path."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _write_yaml_config(project_dir, max_parallel=5)
        tasks_dir = project_dir / ".cognitive-os" / "tasks"
        _write_active_tasks(tasks_dir, in_progress=0)

        result = _run_hook(project_dir)
        assert result.returncode == 0
        combined = result.stderr + result.stdout
        assert "MODEL_ADVICE" in combined or "Model:" in combined, (
            f"No model advice found in output; stderr={result.stderr[:400]}"
        )


# ---------------------------------------------------------------------------
# Config reading
# ---------------------------------------------------------------------------

class TestConfigReading:
    def test_reads_max_parallel_from_yaml(self, tmp_path):
        """Hook reads max_parallel_agents from cognitive-os.yaml (not hardcoded)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        # Set limit to 2, put 2 in-progress → should block
        _write_yaml_config(project_dir, max_parallel=2)
        tasks_dir = project_dir / ".cognitive-os" / "tasks"
        _write_active_tasks(tasks_dir, in_progress=2)

        result = _run_hook(project_dir)
        assert result.returncode == 2, (
            "Hook should block when YAML limit=2 and active=2; "
            f"got {result.returncode}; stderr={result.stderr[:300]}"
        )

    def test_yaml_limit_8_allows_5_agents(self, tmp_path):
        """When YAML sets limit=8 and only 5 are active, hook allows."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _write_yaml_config(project_dir, max_parallel=8)
        tasks_dir = project_dir / ".cognitive-os" / "tasks"
        _write_active_tasks(tasks_dir, in_progress=5)

        result = _run_hook(project_dir)
        assert result.returncode == 0, (
            f"Expected allow with limit=8 active=5; got {result.returncode}; "
            f"stderr={result.stderr[:300]}"
        )


# ---------------------------------------------------------------------------
# Task counting
# ---------------------------------------------------------------------------

class TestTaskCounting:
    def test_counts_in_progress_tasks(self, tmp_path):
        """Only 'in_progress' tasks are counted — completed tasks are ignored."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _write_yaml_config(project_dir, max_parallel=3)
        tasks_dir = project_dir / ".cognitive-os" / "tasks"
        # 2 completed, 1 in_progress → total in_progress = 1 < 3
        _write_active_tasks(tasks_dir, in_progress=1, completed=5)

        result = _run_hook(project_dir)
        assert result.returncode == 0, (
            "Completed tasks must not count towards slot usage; "
            f"got {result.returncode}; stderr={result.stderr[:300]}"
        )

    def test_no_tasks_file_defaults_to_zero_active(self, tmp_path):
        """Missing active-tasks.json means 0 active — hook should allow."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _write_yaml_config(project_dir, max_parallel=5)
        # No tasks file written

        result = _run_hook(project_dir)
        assert result.returncode == 0, (
            f"Missing tasks file should default to 0 active; "
            f"got {result.returncode}; stderr={result.stderr[:300]}"
        )
