"""Tests for hooks/surface-fix-detector.sh — advisory surface-fix detection.

The hook is advisory (always exits 0). These tests assert the presence or
absence of the advisory banner in stdout for representative inputs.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "surface-fix-detector.sh"
ADVISORY_MARKER = "[surface-fix-detector] ADVISORY"


def _run_hook(payload: dict, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        check=False,
    )


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    return tmp_path


@pytest.mark.skipif(not shutil.which("jq"), reason="jq required")
def test_triggers_on_additions_only_clarifying_prose(tmp_project: Path) -> None:
    """Write tool adding 5+ lines of clarification prose should trigger the advisory."""
    payload = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(tmp_project / "docs" / "note.md"),
            "content": (
                "# Note\n"
                "To clarify the earlier discussion:\n"
                "This is an explanatory addition.\n"
                "Note: values were already consistent.\n"
                "See also: the clarification in ADR-047.\n"
            ),
        },
    }
    result = _run_hook(payload, tmp_project)
    assert result.returncode == 0, result.stderr
    assert ADVISORY_MARKER in result.stdout, (
        f"Expected advisory on clarification-only Write, got:\n{result.stdout}"
    )


@pytest.mark.skipif(not shutil.which("jq"), reason="jq required")
def test_does_not_trigger_on_code_change(tmp_project: Path) -> None:
    """Edit that substantively changes code (no trigger words) must stay silent."""
    payload = {
        "tool_name": "Edit",
        "tool_input": {
            "file_path": str(tmp_project / "lib" / "thing.py"),
            "old_string": "_THRESHOLD = 1.0\n",
            "new_string": "_THRESHOLD = 5.0\n",
        },
    }
    result = _run_hook(payload, tmp_project)
    assert result.returncode == 0, result.stderr
    assert ADVISORY_MARKER not in result.stdout, (
        f"Advisory should NOT fire for code change, got:\n{result.stdout}"
    )


@pytest.mark.skipif(not shutil.which("jq"), reason="jq required")
def test_does_not_trigger_without_trigger_words(tmp_project: Path) -> None:
    """A pure-additions Write with no clarifying words must not trigger."""
    payload = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(tmp_project / "src" / "foo.py"),
            "content": (
                "def add(a, b):\n"
                "    return a + b\n"
                "def sub(a, b):\n"
                "    return a - b\n"
                "def mul(a, b):\n"
                "    return a * b\n"
            ),
        },
    }
    result = _run_hook(payload, tmp_project)
    assert result.returncode == 0, result.stderr
    assert ADVISORY_MARKER not in result.stdout, (
        f"Advisory should NOT fire without trigger words, got:\n{result.stdout}"
    )


@pytest.mark.skipif(not shutil.which("jq"), reason="jq required")
def test_ignores_unrelated_tool(tmp_project: Path) -> None:
    """Bash tool calls should be ignored entirely."""
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "echo clarification"},
    }
    result = _run_hook(payload, tmp_project)
    assert result.returncode == 0
    assert ADVISORY_MARKER not in result.stdout


@pytest.mark.skipif(not shutil.which("jq"), reason="jq required")
def test_logs_advisory_to_jsonl(tmp_project: Path) -> None:
    """When the advisory fires, a JSONL entry is written to metrics."""
    payload = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(tmp_project / "docs" / "clarify.md"),
            "content": (
                "# Clarify\n"
                "Nota: to clarify the constants.\n"
                "This is explanatory prose.\n"
                "Note: no values changed.\n"
                "Just clarification.\n"
            ),
        },
    }
    result = _run_hook(payload, tmp_project)
    assert result.returncode == 0
    log = tmp_project / ".cognitive-os" / "metrics" / "surface-fix-detector.jsonl"
    assert log.exists(), "JSONL log file should have been created"
    entries = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    assert entries, "Expected at least one log entry"
    assert entries[-1]["tool"] == "Write"
    assert entries[-1]["additions_ratio"] >= 90
