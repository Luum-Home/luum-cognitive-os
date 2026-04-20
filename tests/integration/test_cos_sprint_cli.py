"""Integration tests for scripts/cos-sprint.py (ADR-036 MVP)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
SCRIPT = _REPO / "scripts" / "cos-sprint.py"
EXAMPLE = _REPO / ".cognitive-os" / "sprints" / "example-sprint.yaml"


def _run_cli(args: list[str], project_dir: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir), "PYTHONPATH": str(_REPO)}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(project_dir),
    )


@pytest.fixture
def fake_project(tmp_path: Path) -> Path:
    """Create a minimal fake project that shares the real repo's lib/ via sys.path."""
    # Copy only the example spec into the fake project so `run` has something to load.
    sprints = tmp_path / ".cognitive-os" / "sprints"
    sprints.mkdir(parents=True)
    shutil.copy(EXAMPLE, sprints / "example-sprint.yaml")
    return tmp_path


def test_run_produces_manifest(fake_project: Path) -> None:
    spec = fake_project / ".cognitive-os" / "sprints" / "example-sprint.yaml"
    result = _run_cli(["run", str(spec)], fake_project)
    assert result.returncode == 0, result.stderr
    assert "manifest:" in result.stdout
    assert "tasks:    3" in result.stdout

    # Exactly one manifest JSON created.
    manifests = list((fake_project / ".cognitive-os" / "sprints").glob("sprint-*.json"))
    assert len(manifests) == 1
    data = json.loads(manifests[0].read_text())
    assert data["name"] == "example-mvp-sprint"
    assert data["status"] == "pending"
    assert len(data["tasks"]) == 3

    # SprintStarted emitted to canonical events.
    events = (fake_project / ".cognitive-os" / "metrics" / "canonical-events.jsonl").read_text()
    assert '"event_type": "sprint_started"' in events


def test_list_shows_entries(fake_project: Path) -> None:
    spec = fake_project / ".cognitive-os" / "sprints" / "example-sprint.yaml"
    _run_cli(["run", str(spec)], fake_project)

    result = _run_cli(["list"], fake_project)
    assert result.returncode == 0
    assert "example-mvp-sprint" in result.stdout
    assert "pending" in result.stdout

    json_result = _run_cli(["list", "--json"], fake_project)
    assert json_result.returncode == 0
    payload = json.loads(json_result.stdout)
    assert len(payload) == 1
    assert payload[0]["name"] == "example-mvp-sprint"


def test_status_renders_manifest(fake_project: Path) -> None:
    spec = fake_project / ".cognitive-os" / "sprints" / "example-sprint.yaml"
    run_result = _run_cli(["run", str(spec)], fake_project)
    # Extract sprint id from stdout ("sprint: sprint-xxxxxxxx")
    sprint_line = [ln for ln in run_result.stdout.splitlines() if ln.startswith("sprint:")][0]
    sprint_id = sprint_line.split(":", 1)[1].strip()

    status = _run_cli(["status", sprint_id], fake_project)
    assert status.returncode == 0, status.stderr
    assert "example-mvp-sprint" in status.stdout
    assert "Status: pending" in status.stdout
    assert "fix-login-bug" in status.stdout


def test_cancel_updates_state(fake_project: Path) -> None:
    spec = fake_project / ".cognitive-os" / "sprints" / "example-sprint.yaml"
    run_result = _run_cli(["run", str(spec)], fake_project)
    sprint_id = [ln for ln in run_result.stdout.splitlines() if ln.startswith("sprint:")][0].split(":", 1)[1].strip()

    cancel = _run_cli(["cancel", sprint_id, "--reason", "test"], fake_project)
    assert cancel.returncode == 0, cancel.stderr
    assert "cancelled" in cancel.stdout

    # Manifest on disk now shows cancelled.
    manifest_file = fake_project / ".cognitive-os" / "sprints" / f"{sprint_id}.json"
    data = json.loads(manifest_file.read_text())
    assert data["status"] == "cancelled"
    assert data["ended_at"] is not None

    # SprintCancelled event was emitted.
    events = (fake_project / ".cognitive-os" / "metrics" / "canonical-events.jsonl").read_text()
    assert '"event_type": "sprint_cancelled"' in events

    # Double-cancel should fail (terminal state).
    double = _run_cli(["cancel", sprint_id], fake_project)
    assert double.returncode == 3
