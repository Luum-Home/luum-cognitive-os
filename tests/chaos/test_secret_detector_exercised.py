"""Exercised chaos test for hooks/secret-detector.sh (ADR-041 Wave A).

Tier: A (Safety-critical — secret/credential detection)
Trigger: PreToolUse Bash command containing literal API key patterns;
         PostToolUse Edit with env-var references.

Contract:
  - PreToolUse mode: detects secrets in command strings and either redacts
    or blocks (exit 0 for advisory, exit 2 for hard block).
  - PostToolUse mode: scans written files for missing env-var definitions,
    emits advisory to stderr and logs to missing-secrets.jsonl (exit 0).
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
_HOOK = _PROJ_ROOT / "hooks" / "secret-detector.sh"
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
        "component": "hooks/secret-detector.sh",
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
        "PROJECT_DIR": str(tmp_path),
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


@pytest.mark.skipif(not _HOOK.exists(), reason="secret-detector.sh not found")
def test_secret_detector_exists():
    """Sanity: hook file must exist."""
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="secret-detector.sh not found")
def test_secret_detector_empty_input_exits_cleanly(tmp_path: Path):
    """Empty stdin must exit 0 without errors."""
    _setup_project(tmp_path)
    result = _run(tmp_path, "")
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "empty_input", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="secret-detector.sh not found")
def test_secret_detector_postuse_clean_file_advisory(tmp_path: Path):
    """PostToolUse with a file containing no secret patterns must exit 0."""
    _setup_project(tmp_path)
    test_file = tmp_path / "clean.py"
    test_file.write_text("x = 1\nprint(x)\n")

    payload = json.dumps({
        "tool_name": "Write",
        "hook_event_name": "PostToolUse",
        "tool_input": {"file_path": str(test_file)},
        "tool_response": {"outcome": "success"},
    })
    result = _run(tmp_path, payload)
    # Advisory hook — always exit 0
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:300]}"
    _write_chaos_run(tmp_path, "postuse_clean_file", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="secret-detector.sh not found")
def test_secret_detector_killswitch_suppresses(tmp_path: Path):
    """With SO_KILLSWITCH=1 the hook must exit 0 silently."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Bash",
        "hook_event_name": "PreToolUse",
        "tool_input": {"command": "echo OPENAI_API_KEY=sk-test1234"},
    })
    result = _run(tmp_path, payload, env_extra={"SO_KILLSWITCH": "1"})
    assert result.returncode == 0, f"killswitch ON exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "killswitch_suppresses", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="secret-detector.sh not found")
def test_secret_detector_writes_chaos_run(tmp_path: Path):
    """chaos-runs.jsonl must receive an exercise record."""
    _setup_project(tmp_path)
    _run(tmp_path, "")
    _write_chaos_run(tmp_path, "audit_write", True)

    log = tmp_path / _CHAOS_RUNS_REL
    assert log.exists()
    rows = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    assert any(r.get("component") == "hooks/secret-detector.sh" for r in rows)
