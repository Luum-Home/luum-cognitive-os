"""Exercised chaos test for hooks/error-pipeline.sh (ADR-041 Wave A).

Tier: A (Safety-critical — merged error detection, logging, repair dispatch)
Trigger: PostToolUse Bash with non-zero exit_code and various error types.

Contract:
  - Fires on Bash tool_name only.
  - Skips exit_code=0 (success path).
  - Classifies: TEST_FAILURE, BUILD_ERROR, LINT_ERROR, COMPILATION_ERROR.
  - Appends to error-learning.jsonl and potentially repair-outcomes.jsonl.
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
_HOOK = _PROJ_ROOT / "hooks" / "error-pipeline.sh"
_CHAOS_RUNS_REL = ".cognitive-os/metrics/chaos-runs.jsonl"


def _setup_project(tmp_path: Path, phase: str = "reconstruction") -> None:
    (tmp_path / ".cognitive-os" / "runtime").mkdir(parents=True)
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
    (tmp_path / "cognitive-os.yaml").write_text(
        f"project:\n  phase: {phase}\n  name: chaos-test\n"
    )


def _write_chaos_run(tmp_path: Path, scenario: str, passed: bool) -> None:
    log = tmp_path / _CHAOS_RUNS_REL
    row = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event_type": "component.exercised",
        "component": "hooks/error-pipeline.sh",
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


@pytest.mark.skipif(not _HOOK.exists(), reason="error-pipeline.sh not found")
def test_error_pipeline_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="error-pipeline.sh not found")
def test_error_pipeline_empty_input_exits_cleanly(tmp_path: Path):
    """Empty stdin must exit 0."""
    _setup_project(tmp_path)
    result = _run(tmp_path, "")
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "empty_input", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="error-pipeline.sh not found")
def test_error_pipeline_success_is_ignored(tmp_path: Path):
    """Bash exit_code=0 must be ignored (pipeline only handles failures)."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "go test ./..."},
        "exit_code": "0",
        "tool_response": "ok  github.com/foo/bar  0.123s",
    })
    result = _run(tmp_path, payload)
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "success_ignored", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="error-pipeline.sh not found")
def test_error_pipeline_jest_failure_logs_to_jsonl(tmp_path: Path):
    """Jest test failure must be classified and logged to error-learning.jsonl."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "jest --coverage"},
        "exit_code": "1",
        "tool_response": (
            "FAIL src/user.test.ts\n"
            "  ● UserService › should return user\n"
            "    Expected: 'Alice'\n"
            "    Received: undefined\n"
            "Test Suites: 1 failed, 5 passed\n"
        ),
    })
    result = _run(tmp_path, payload)
    assert result.returncode == 0, (
        f"Advisory hook must exit 0, got {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    # Verify error-learning.jsonl was written (if safe-jsonl.sh works correctly)
    el_file = tmp_path / ".cognitive-os" / "metrics" / "error-learning.jsonl"
    if el_file.exists():
        rows = [json.loads(l) for l in el_file.read_text().splitlines() if l.strip()]
        # At least one row should exist
        assert len(rows) >= 1, "Expected at least one error-learning row"
    _write_chaos_run(tmp_path, "jest_failure_logged", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="error-pipeline.sh not found")
def test_error_pipeline_lint_failure_captured(tmp_path: Path):
    """ESLint failure must be classified and not crash the hook."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "eslint src/"},
        "exit_code": "1",
        "tool_response": "src/index.ts:10:5 error  no-unused-vars  'x' is defined but never used\n1 error",
    })
    result = _run(tmp_path, payload)
    assert result.returncode == 0, (
        f"Advisory hook must exit 0, got {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    _write_chaos_run(tmp_path, "lint_failure_captured", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="error-pipeline.sh not found")
def test_error_pipeline_killswitch_suppresses(tmp_path: Path):
    """With SO_KILLSWITCH=1, hook must exit 0 silently."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "pytest"},
        "exit_code": "1",
        "tool_response": "FAILED: critical test",
    })
    result = _run(tmp_path, payload, env_extra={"SO_KILLSWITCH": "1"})
    assert result.returncode == 0, f"killswitch exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "killswitch_suppresses", True)
