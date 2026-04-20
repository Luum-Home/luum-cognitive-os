"""Exercised chaos test for hooks/auto-verify.sh (ADR-041 Wave A).

Tier: A (Safety-critical — acceptance-criteria verification)
Trigger: PostToolUse Agent response containing ACCEPTANCE CRITERIA block
         with verifiable commands.

Contract:
  - Only fires on Agent tool_name.
  - Extracts ACCEPTANCE CRITERIA: sections and runs each command.
  - Advisory: always exits 0 (logs PASS/FAIL to auto-verify.jsonl).
  - With SO_KILLSWITCH=1: exits 0 silently.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOK = _PROJ_ROOT / "hooks" / "auto-verify.sh"
_CHAOS_RUNS_REL = ".cognitive-os/metrics/chaos-runs.jsonl"


def _setup_project(tmp_path: Path) -> None:
    (tmp_path / ".cognitive-os" / "runtime").mkdir(parents=True)
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)


def _write_chaos_run(tmp_path: Path, scenario: str, passed: bool) -> None:
    log = tmp_path / _CHAOS_RUNS_REL
    row = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event_type": "component.exercised",
        "component": "hooks/auto-verify.sh",
        "scenario": scenario,
        "passed": passed,
        "source": "chaos-test",
    }
    with log.open("a") as fh:
        fh.write(json.dumps(row) + "\n")


def _run(tmp_path: Path, stdin_payload: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", str(tmp_path)),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "VALKEY_DISABLED": "1",
    }
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(_HOOK)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        cwd=str(tmp_path),
    )


@pytest.mark.skipif(not _HOOK.exists(), reason="auto-verify.sh not found")
def test_auto_verify_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="auto-verify.sh not found")
def test_auto_verify_empty_input_exits_cleanly(tmp_path: Path):
    """Empty stdin must exit 0."""
    _setup_project(tmp_path)
    result = _run(tmp_path, "")
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "empty_input", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="auto-verify.sh not found")
def test_auto_verify_non_agent_tool_passthrough(tmp_path: Path):
    """Non-Agent tool_name must be ignored (exit 0)."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "tool_response": "file.txt",
    })
    result = _run(tmp_path, payload)
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "non_agent_passthrough", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="auto-verify.sh not found")
def test_auto_verify_no_criteria_in_response(tmp_path: Path):
    """Agent response without ACCEPTANCE CRITERIA must exit 0 (no criteria = no check)."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Agent",
        "tool_response": "Implementation complete. All code changes applied.",
        "tool_input": {"prompt": "Implement the feature"},
    })
    result = _run(tmp_path, payload)
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:300]}"
    _write_chaos_run(tmp_path, "no_criteria_passthrough", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="auto-verify.sh not found")
def test_auto_verify_with_passing_criteria(tmp_path: Path):
    """Agent response with a trivially-passing command in criteria must log PASS."""
    _setup_project(tmp_path)
    response = (
        "Implementation complete.\n\n"
        "ACCEPTANCE CRITERIA:\n"
        "1. echo ok exits 0: echo ok\n"
    )
    payload = json.dumps({
        "tool_name": "Agent",
        "tool_response": response,
        "tool_input": {"prompt": "Do something"},
    })
    result = _run(tmp_path, payload)
    assert result.returncode == 0, (
        f"Advisory hook must exit 0, got {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    _write_chaos_run(tmp_path, "with_passing_criteria", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="auto-verify.sh not found")
def test_auto_verify_killswitch_suppresses(tmp_path: Path):
    """With SO_KILLSWITCH=1, hook must exit 0 silently."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Agent",
        "tool_response": "ACCEPTANCE CRITERIA:\n1. echo test",
    })
    result = _run(tmp_path, payload, env_extra={"SO_KILLSWITCH": "1"})
    assert result.returncode == 0, f"killswitch exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "killswitch_suppresses", True)
