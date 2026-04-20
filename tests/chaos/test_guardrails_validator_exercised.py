"""Exercised chaos test for hooks/guardrails-validator.sh (ADR-041 Wave A).

Tier: A (Safety-critical — PII detection on agent output)
Feature-gated: GUARDRAILS_ENABLED=true required to activate validation.

Contract:
  - OFF by default: exits 0 silently when GUARDRAILS_ENABLED != "true".
  - When enabled: fires on Agent tool_name only.
  - Scans agent output for PII patterns via lib/guardrails_validators.py.
  - Advisory: always exits 0 (warns on PII detection).
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
_HOOK = _PROJ_ROOT / "hooks" / "guardrails-validator.sh"
_VALIDATORS_LIB = _PROJ_ROOT / "lib" / "guardrails_validators.py"
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
        "component": "hooks/guardrails-validator.sh",
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


@pytest.mark.skipif(not _HOOK.exists(), reason="guardrails-validator.sh not found")
def test_guardrails_validator_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="guardrails-validator.sh not found")
def test_guardrails_validator_off_by_default(tmp_path: Path):
    """Without GUARDRAILS_ENABLED=true, hook must exit 0 silently (feature-gated)."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Agent",
        "tool_response": "User john.doe@example.com called us at 555-1234.",
    })
    # No GUARDRAILS_ENABLED → should exit 0 immediately
    result = _run(tmp_path, payload)
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "off_by_default", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="guardrails-validator.sh not found")
def test_guardrails_validator_empty_input_exits_cleanly(tmp_path: Path):
    """Empty stdin must exit 0."""
    _setup_project(tmp_path)
    result = _run(tmp_path, "")
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "empty_input", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="guardrails-validator.sh not found")
def test_guardrails_validator_killswitch_suppresses(tmp_path: Path):
    """With SO_KILLSWITCH=1, hook must exit 0 silently."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Agent",
        "tool_response": "some response",
    })
    result = _run(
        tmp_path, payload,
        env_extra={"SO_KILLSWITCH": "1", "GUARDRAILS_ENABLED": "true"},
    )
    assert result.returncode == 0, f"killswitch exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "killswitch_suppresses", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="guardrails-validator.sh not found")
@pytest.mark.skipif(
    not _VALIDATORS_LIB.exists(),
    reason="lib/guardrails_validators.py not found — feature not fully available",
)
def test_guardrails_validator_enabled_clean_response(tmp_path: Path):
    """With GUARDRAILS_ENABLED=true and clean response, hook must exit 0."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Agent",
        "tool_response": "The implementation is complete. All tests pass.",
    })
    result = _run(tmp_path, payload, env_extra={"GUARDRAILS_ENABLED": "true"})
    assert result.returncode == 0, (
        f"Advisory hook must exit 0, got {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    _write_chaos_run(tmp_path, "enabled_clean_response", True)
