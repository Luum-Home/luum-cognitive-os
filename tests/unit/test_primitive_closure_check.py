from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts import cos_primitive_closure_check as closure

pytestmark = pytest.mark.unit


def completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> Mock:
    proc = Mock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def test_context_marks_primitive_changes_as_requiring_closure() -> None:
    with patch.object(
        closure,
        "changed_paths",
        return_value={"scripts/cos-new-primitive", "README.md", ".ai/context.json"},
    ):
        context = closure.closure_context()

    assert context["requires_primitive_closure"] is True
    assert context["primitive_changed_count"] == 1
    assert context["derived_changed_count"] == 1


def test_run_checks_reports_failed_remediation() -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, timeout: int = 180) -> Mock:
        calls.append(command)
        if any("portable_ai_overlay.py" in part for part in command):
            return completed(1, stderr="stale overlay")
        return completed(0, stdout="ok")

    with patch.object(closure, "_run", side_effect=fake_run):
        steps = closure.run_checks()

    assert calls
    failed = [step for step in steps if step.status == "fail"]
    assert [step.id for step in failed] == ["portable-ai-overlay"]
    assert "portable_ai_overlay.py" in failed[0].remediation


def test_json_report_is_serializable() -> None:
    with patch.object(closure, "run_checks", return_value=[]), patch.object(closure, "closure_context", return_value={"requires_primitive_closure": False}):
        payload = closure.build_report(repair=False)

    assert payload["status"] == "pass"
    json.dumps(payload)
