"""Contracts for automatic SessionStart tooling checks.

These tests keep the host-health loop real without letting broad test execution
creep back into agent startup.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml


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


def test_codex_projection_preserves_hook_exit_codes() -> None:
    """Codex hooks must not turn blocking hook exits into success.

    Missing hook scripts should remain harmless during first install, but once a
    hook exists its exit code is the hook decision.  Appending ``|| true`` would
    silently disable Codex Bash safety gates such as destructive command blocks.
    """

    settings = json.loads((PROJECT_ROOT / ".codex" / "hooks.json").read_text())
    commands = _commands(settings)

    assert commands, "Codex projection should contain hook commands"
    assert not [command for command in commands if "|| true" in command]
    assert all("if [ -x " in command for command in commands)


def test_generated_codex_projection_preserves_hook_exit_codes() -> None:
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
    commands = _commands(settings)
    assert commands
    assert not [command for command in commands if "|| true" in command]


def test_generated_codex_projection_uses_supported_native_surface() -> None:
    """The generated projection must sit inside the surface Codex publishes.

    The expected surface is read from ``manifests/codex-hooks-schema.yaml`` (the
    transcribed upstream contract, with its source URLs and verification date)
    rather than hard-coded here.  A previous version of this test hard-coded the
    pre-2026-08-15 driver output — event keys at the root with no ``hooks``
    namespace, ``matcher: "prompt"`` on UserPromptSubmit, ``matcher: "shutdown"``
    on Stop, and Bash-only tool matchers.  All four are schema violations, so the
    test was pinning the defect instead of catching it.
    """

    schema = yaml.safe_load(
        (PROJECT_ROOT / "manifests" / "codex-hooks-schema.yaml").read_text()
    )
    events = schema["events"]
    published_tools = {
        entry["name"] for entry in schema["tool_names"] if "name" in entry
    }

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

    # The `hooks` namespace is mandatory: event keys at the root are not parsed
    # as hooks at all, which makes the whole registration inert.
    root_key = schema["file"]["root_key"]
    assert schema["file"]["root_key_required"] is True
    assert set(settings) == {root_key}, (
        f"projection must nest events under {root_key!r}, got {sorted(settings)}"
    )
    hooks = settings[root_key]
    assert hooks, "projection emitted no events"

    unknown = set(hooks) - set(events)
    assert not unknown, f"events absent from the published schema: {sorted(unknown)}"

    for event, groups in hooks.items():
        support = events[event]["matcher"]
        matchers = [group.get("matcher") for group in groups]

        if support == "unsupported":
            assert all(matcher is None for matcher in matchers), (
                f"{event} does not accept a matcher; emitting one is a schema "
                f"violation, got {matchers}"
            )
            continue

        if support == "required":
            assert all(matcher is not None for matcher in matchers), event

        present = [matcher for matcher in matchers if matcher is not None]
        semantics = events[event].get("matcher_semantics")
        if semantics == "enum":
            allowed = set(events[event]["matcher_values"])
            assert set(present) <= allowed, f"{event}: {present} not in {sorted(allowed)}"
        elif semantics == "tool_name_regex":
            for matcher in present:
                assert any(
                    re.search(matcher, tool) for tool in published_tools
                ), f"{event}: matcher {matcher!r} matches no published tool name"


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


def test_host_tool_doctor_includes_memory_lifecycle_doctor_without_pytest() -> None:
    content = (PROJECT_ROOT / "scripts" / "cos-doctor-tools.sh").read_text()

    assert "cos-doctor-memory-lifecycle.sh" in content
    assert "pytest-with-summary.sh" not in content
    assert "python3 -m pytest" not in content


def test_codex_has_no_missing_projection_on_supported_driver_events() -> None:
    result = subprocess.run(
        [
            "python3",
            str(PROJECT_ROOT / "scripts" / "harness_parity_audit.py"),
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
