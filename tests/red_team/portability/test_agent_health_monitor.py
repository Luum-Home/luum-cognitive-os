# SCOPE: os-only
"""Portability proof for cos_lib/agent_health_monitor.py.

``agent_health_monitor`` backs ``hooks/completion-gate.sh`` (SCOPE: both), a
consumer-facing PostToolUse hook on Agent. This proof pins that the module
imports and its primary entry point (``AgentHealthMonitor.check_health``)
works from an arbitrary consumer project directory, reading only
``.cognitive-os/tasks/active-tasks.json`` and ``cognitive-os.yaml`` relative
to the project dir -- never anything that assumes the Cognitive OS source
repo itself.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/agent_health_monitor.py"


def test_agent_health_monitor_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_agent_health_monitor", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_check_health_classifies_timeout_in_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: exercise the real entry point in a throwaway project.

    Writes an ``active-tasks.json`` with one long-running, no-PID task under
    a project dir that is NOT the Cognitive OS source repo, then confirms
    ``check_health`` classifies it as "timeout" using the configured
    ``agent_timeout_seconds`` -- proving classification depends only on the
    supplied project dir's own files, not on OS-repo paths or manifests.
    """
    project_dir = tmp_path / "consumer-project"
    tasks_dir = project_dir / ".cognitive-os" / "tasks"
    tasks_dir.mkdir(parents=True)

    stale_started_at = (datetime.now(timezone.utc) - timedelta(seconds=600)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    tasks_payload = {
        "tasks": [
            {
                "id": "task-1",
                "status": "in_progress",
                "description": "long running task",
                "started_at": stale_started_at,
            }
        ]
    }
    (tasks_dir / "active-tasks.json").write_text(json.dumps(tasks_payload))
    (project_dir / "cognitive-os.yaml").write_text("agent_timeout_seconds: 60\n")

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.agent_health_monitor import AgentHealthMonitor\n"
        "monitor = AgentHealthMonitor(tasks_path=%r, config_path=%r)\n"
        "health = monitor.check_health()\n"
        "print(len(health['timeout']))\n"
        "print(health['timeout'][0]['id'] if health['timeout'] else '')\n"
    ) % (
        str(REPO_ROOT),
        str(tasks_dir / "active-tasks.json"),
        str(project_dir / "cognitive-os.yaml"),
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert lines[0] == "1"
    assert lines[1] == "task-1"
