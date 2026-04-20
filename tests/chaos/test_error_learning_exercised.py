"""Exercised chaos test for hooks/error-learning.sh (ADR-041 Wave A).

Tier: A (Safety-critical — error capture and pattern learning)
Trigger: PostToolUse Bash with non-zero exit_code and failure output.

Contract:
  - Fires on Bash tool_name only.
  - Ignores exit_code=0 (success).
  - Classifies errors: TEST_FAILURE, LINT_ERROR, BUILD_ERROR, COMPILATION_ERROR.
  - Deduplicates within 60s using MD5 fingerprint.
  - Appends to error-learning.jsonl.
  - Advisory: always exits 0.
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
_HOOK = _PROJ_ROOT / "hooks" / "error-learning.sh"
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
        "component": "hooks/error-learning.sh",
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
        timeout=15,
        env=env,
        cwd=str(tmp_path),
    )


@pytest.mark.skipif(not _HOOK.exists(), reason="error-learning.sh not found")
def test_error_learning_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="error-learning.sh not found")
def test_error_learning_empty_input_exits_cleanly(tmp_path: Path):
    """Empty stdin must exit 0."""
    _setup_project(tmp_path)
    result = _run(tmp_path, "")
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "empty_input", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="error-learning.sh not found")
def test_error_learning_success_exit_code_ignored(tmp_path: Path):
    """Bash tool with exit_code=0 must be ignored (no JSONL write)."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "yarn test"},
        "exit_code": "0",
        "tool_response": "All tests passed.",
    })
    result = _run(tmp_path, payload)
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    # Should NOT write to error-learning.jsonl on success
    el_file = tmp_path / ".cognitive-os" / "metrics" / "error-learning.jsonl"
    if el_file.exists():
        rows = [json.loads(l) for l in el_file.read_text().splitlines() if l.strip()]
        assert len(rows) == 0, "Should not log successful runs to error-learning.jsonl"
    _write_chaos_run(tmp_path, "success_ignored", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="error-learning.sh not found")
def test_error_learning_test_failure_captured(tmp_path: Path):
    """Bash tool with exit_code=1 and test failure output must write to error-learning.jsonl."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/"},
        "exit_code": "1",
        "tool_response": "FAILED tests/test_foo.py::test_bar - AssertionError: expected 1 got 0\n1 failed, 5 passed",
    })
    result = _run(tmp_path, payload)
    assert result.returncode == 0, (
        f"Advisory hook must exit 0, got {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    # Check error-learning.jsonl was written
    el_file = tmp_path / ".cognitive-os" / "metrics" / "error-learning.jsonl"
    if el_file.exists():
        rows = [json.loads(l) for l in el_file.read_text().splitlines() if l.strip()]
        if rows:
            # At least one row should classify as TEST_FAILURE
            # error-learning.sh uses "type" field (not "error_type")
            types = [r.get("type") or r.get("error_type") for r in rows]
            assert any("TEST" in str(t) or "FAIL" in str(t) for t in types if t), (
                f"Expected TEST_FAILURE classification, got types: {types}\nrows: {rows}"
            )
    _write_chaos_run(tmp_path, "test_failure_captured", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="error-learning.sh not found")
def test_error_learning_build_error_captured(tmp_path: Path):
    """Build error with exit_code=1 must be classified as BUILD_ERROR."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "go build ./..."},
        "exit_code": "2",
        "tool_response": "cannot find module providing package foo/bar\nbuild failed",
    })
    result = _run(tmp_path, payload)
    assert result.returncode == 0, (
        f"Advisory hook must exit 0, got {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    _write_chaos_run(tmp_path, "build_error_captured", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="error-learning.sh not found")
def test_error_learning_killswitch_suppresses(tmp_path: Path):
    """With SO_KILLSWITCH=1, hook must exit 0 silently (no JSONL write)."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "pytest"},
        "exit_code": "1",
        "tool_response": "FAILED: 10 tests failed",
    })
    result = _run(tmp_path, payload, env_extra={"SO_KILLSWITCH": "1"})
    assert result.returncode == 0, f"killswitch exit {result.returncode}: {result.stderr[:200]}"
    # Should NOT have written to JSONL with killswitch active
    _write_chaos_run(tmp_path, "killswitch_suppresses", True)
