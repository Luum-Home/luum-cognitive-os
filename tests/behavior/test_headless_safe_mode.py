"""Behavior tests for the headless safe-mode admission primitive."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLI = PROJECT_ROOT / "scripts" / "cos_headless_safe_mode.py"
WRAPPER = PROJECT_ROOT / "scripts" / "cos-headless-safe-mode"


def run_cli(project_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the safe-mode CLI against a temporary project."""
    return subprocess.run(
        ["python3", str(CLI), *args, "--project-dir", str(project_dir), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )


def read_json(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    """Parse CLI JSON output."""
    return json.loads(result.stdout)


def test_status_defaults_to_admitting_new_tasks(tmp_path: Path) -> None:
    """Missing state is local-safe and allows task admission."""
    payload = read_json(run_cli(tmp_path, "status"))

    assert payload["safe_mode"] is False
    assert payload["admits_new_tasks"] is True
    assert payload["reason"] is None
    assert payload["state_path"].endswith(
        ".cognitive-os/runtime/headless-safe-mode.json"
    )


def test_enable_blocks_task_admission_and_records_reason_timestamp(tmp_path: Path) -> None:
    """Enabling safe mode blocks new tasks and records operator context."""
    payload = read_json(run_cli(tmp_path, "enable", "--reason", "incident triage"))

    assert payload["safe_mode"] is True
    assert payload["admits_new_tasks"] is False
    assert payload["reason"] == "incident triage"
    assert isinstance(payload["updated_at"], str)
    assert payload["updated_at"]

    status = read_json(run_cli(tmp_path, "status"))
    assert status["safe_mode"] is True
    assert status["admits_new_tasks"] is False
    assert status["reason"] == "incident triage"
    assert status["updated_at"] == payload["updated_at"]


def test_disable_allows_task_admission(tmp_path: Path) -> None:
    """Disabling safe mode reopens admission for new headless tasks."""
    run_cli(tmp_path, "enable", "--reason", "operator pause")

    payload = read_json(run_cli(tmp_path, "disable", "--reason", "repair complete"))

    assert payload["safe_mode"] is False
    assert payload["admits_new_tasks"] is True
    assert payload["reason"] == "repair complete"
    assert isinstance(payload["updated_at"], str)
    assert payload["updated_at"]


def test_enable_does_not_remove_existing_artifact_directories(tmp_path: Path) -> None:
    """Safe mode is repair-first and must not destroy in-flight evidence."""
    artifact_dir = tmp_path / ".cognitive-os" / "artifacts" / "task-123"
    evidence_file = artifact_dir / "test-summary.txt"
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text("failing test evidence\n", encoding="utf-8")

    run_cli(tmp_path, "enable", "--reason", "kill switch")

    assert artifact_dir.is_dir()
    assert evidence_file.read_text(encoding="utf-8") == "failing test evidence\n"


def test_wrapper_is_valid_bash() -> None:
    """The shell wrapper follows repository wrapper conventions."""
    result = subprocess.run(["bash", "-n", str(WRAPPER)], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
