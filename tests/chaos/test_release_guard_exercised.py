"""Exercised chaos test for hooks/release-guard.sh (ADR-041 Wave A).

Tier: A (Safety-critical — prevents manual release operations)
Trigger: PreToolUse Bash with commands that match manual release patterns.

Contract:
  - Fires on Bash tool_name only.
  - Blocks (exit 2 + "BLOCKED" stderr): echo/printf > VERSION, git tag v*, sed VERSION.
  - Allows (exit 0): git tag -l, git tag -d, git log, unrelated commands.
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
_HOOK = _PROJ_ROOT / "hooks" / "release-guard.sh"
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
        "component": "hooks/release-guard.sh",
        "scenario": scenario,
        "passed": passed,
        "source": "chaos-test",
    }
    with log.open("a") as fh:
        fh.write(json.dumps(row) + "\n")


def _run(tmp_path: Path, command: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": command},
    })
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", str(tmp_path)),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
    }
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(_HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
        cwd=str(tmp_path),
    )


@pytest.mark.skipif(not _HOOK.exists(), reason="release-guard.sh not found")
def test_release_guard_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="release-guard.sh not found")
def test_release_guard_echo_version_is_blocked(tmp_path: Path):
    """echo '1.2.3' > VERSION must be blocked (exit 2)."""
    _setup_project(tmp_path)
    result = _run(tmp_path, "echo '1.2.3' > VERSION")
    assert result.returncode == 2, (
        f"Expected exit 2 (BLOCKED), got {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    assert "BLOCKED" in result.stderr, f"'BLOCKED' not in stderr: {result.stderr[:300]}"
    _write_chaos_run(tmp_path, "echo_version_blocked", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="release-guard.sh not found")
def test_release_guard_git_tag_version_is_blocked(tmp_path: Path):
    """git tag v1.2.3 must be blocked (exit 2)."""
    _setup_project(tmp_path)
    result = _run(tmp_path, "git tag v1.2.3")
    assert result.returncode == 2, (
        f"Expected exit 2 (BLOCKED) for git tag v*, got {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    assert "BLOCKED" in result.stderr, f"'BLOCKED' not in stderr: {result.stderr[:300]}"
    _write_chaos_run(tmp_path, "git_tag_blocked", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="release-guard.sh not found")
def test_release_guard_git_tag_list_is_allowed(tmp_path: Path):
    """git tag -l must be allowed (not a release operation)."""
    _setup_project(tmp_path)
    result = _run(tmp_path, "git tag -l")
    assert result.returncode == 0, (
        f"git tag -l must be allowed, got exit {result.returncode}\n"
        f"stderr: {result.stderr[:200]}"
    )
    _write_chaos_run(tmp_path, "git_tag_list_allowed", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="release-guard.sh not found")
def test_release_guard_unrelated_command_is_allowed(tmp_path: Path):
    """Regular bash command must pass through (exit 0)."""
    _setup_project(tmp_path)
    result = _run(tmp_path, "ls -la")
    assert result.returncode == 0, (
        f"Unrelated command must be allowed, got exit {result.returncode}\n"
        f"stderr: {result.stderr[:200]}"
    )
    _write_chaos_run(tmp_path, "unrelated_allowed", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="release-guard.sh not found")
def test_release_guard_printf_version_is_blocked(tmp_path: Path):
    """printf '2.0.0' > VERSION must be blocked (exit 2)."""
    _setup_project(tmp_path)
    result = _run(tmp_path, "printf '2.0.0' > VERSION")
    assert result.returncode == 2, (
        f"Expected exit 2 (BLOCKED) for printf > VERSION, got {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    _write_chaos_run(tmp_path, "printf_version_blocked", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="release-guard.sh not found")
def test_release_guard_killswitch_suppresses(tmp_path: Path):
    """With SO_KILLSWITCH=1, block must be suppressed (exit 0)."""
    _setup_project(tmp_path)
    result = _run(tmp_path, "echo '9.9.9' > VERSION", env_extra={"SO_KILLSWITCH": "1"})
    assert result.returncode == 0, (
        f"killswitch must suppress block, got exit {result.returncode}\n"
        f"stderr: {result.stderr[:200]}"
    )
    _write_chaos_run(tmp_path, "killswitch_suppresses", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="release-guard.sh not found")
def test_release_guard_empty_command_is_allowed(tmp_path: Path):
    """Empty command must exit 0."""
    _setup_project(tmp_path)
    result = _run(tmp_path, "")
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "empty_command_allowed", True)
