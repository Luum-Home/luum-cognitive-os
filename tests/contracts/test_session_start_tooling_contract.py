"""Contracts for automatic SessionStart tooling checks.

These tests keep the host-health loop real without letting broad test execution
creep back into agent startup.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.contract

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _commands(settings: dict) -> list[str]:
    commands: list[str] = []
    hook_root = settings.get("hooks", settings)
    for groups in hook_root.values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            for hook in group.get("hooks", []):
                command = hook.get("command")
                if isinstance(command, str):
                    commands.append(command)
    return commands


def _session_start_commands(settings: dict) -> list[str]:
    hook_root = settings.get("hooks", settings)
    commands: list[str] = []
    for group in hook_root.get("SessionStart", []):
        for hook in group.get("hooks", []):
            command = hook.get("command")
            if isinstance(command, str):
                commands.append(command)
    return commands


def test_self_hosted_codex_session_start_runs_host_tool_doctor() -> None:
    settings = json.loads((PROJECT_ROOT / ".codex" / "hooks.json").read_text())
    commands = _session_start_commands(settings)

    assert any("host-tool-doctor.sh" in command for command in commands), commands


def test_self_hosted_claude_session_start_runs_host_tool_doctor() -> None:
    settings = json.loads((PROJECT_ROOT / ".claude" / "settings.json").read_text())
    commands = _session_start_commands(settings)

    assert any("host-tool-doctor.sh" in command for command in commands), commands


def test_generated_codex_default_projection_runs_host_tool_doctor() -> None:
    result = subprocess.run(
        [
            "bash",
            str(PROJECT_ROOT / "scripts" / "generate-project-settings.sh"),
            "--default",
            "--harness=codex",
        ],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    settings = json.loads(result.stdout)
    commands = _session_start_commands(settings)
    assert any("host-tool-doctor.sh" in command for command in commands), commands


def test_session_start_does_not_run_pytest_inventory_or_full_suite() -> None:
    codex = json.loads((PROJECT_ROOT / ".codex" / "hooks.json").read_text())
    claude = json.loads((PROJECT_ROOT / ".claude" / "settings.json").read_text())
    commands = [
        *_session_start_commands(codex),
        *_session_start_commands(claude),
    ]

    forbidden = ("pytest-with-summary.sh", "python3 -m pytest", "pytest ")
    offenders = [
        command
        for command in commands
        if any(token in command for token in forbidden)
    ]
    assert offenders == []


def test_host_tool_doctor_hook_is_advisory_not_pytest_runner() -> None:
    content = (PROJECT_ROOT / "hooks" / "host-tool-doctor.sh").read_text()

    assert "cos-doctor-tools.sh" in content
    assert "manifest-check.sh" not in content, (
        "host-tool-doctor should delegate manifest checks through cos-doctor-tools.sh"
    )
    assert "pytest-with-summary.sh" not in content
    assert "python3 -m pytest" not in content


def test_codex_has_no_missing_projection_on_supported_driver_events() -> None:
    result = subprocess.run(
        [
            "python3",
            str(PROJECT_ROOT / "scripts" / "harness-parity-audit.py"),
            "--source",
            "claude",
            "--target",
            "codex",
            "--strict",
            "--json",
        ],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(result.stdout)
    assert report["missing_supported_count"] == 0
    assert report["target_hook_count"] >= 26
    assert report["missing_limited_count"] > 0
