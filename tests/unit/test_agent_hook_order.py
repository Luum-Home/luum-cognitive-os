"""Hook-order contracts for Agent launch safety."""
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _agent_commands(settings_path: Path) -> list[str]:
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    for group in payload["hooks"]["PreToolUse"]:
        if group.get("matcher") == "Agent":
            return [hook["command"] for hook in group["hooks"]]
    raise AssertionError(f"Agent PreToolUse group not found in {settings_path}")


def _assert_prelaunch_before_snapshot(commands: list[str]) -> None:
    prelaunch = next(i for i, cmd in enumerate(commands) if "hooks/agent-prelaunch.sh" in cmd)
    snapshot = next(i for i, cmd in enumerate(commands) if "hooks/pre-agent-snapshot.sh" in cmd)
    assert prelaunch < snapshot, "agent-prelaunch.sh must run before pre-agent-snapshot.sh"


def test_active_claude_settings_run_prelaunch_before_snapshot() -> None:
    _assert_prelaunch_before_snapshot(_agent_commands(PROJECT_ROOT / ".claude/settings.json"))


def test_standard_profile_runs_prelaunch_before_snapshot() -> None:
    _assert_prelaunch_before_snapshot(_agent_commands(PROJECT_ROOT / "templates/security-profiles/standard.json"))


def test_paranoid_profile_runs_prelaunch_before_snapshot() -> None:
    _assert_prelaunch_before_snapshot(_agent_commands(PROJECT_ROOT / "templates/security-profiles/paranoid.json"))


def test_claude_settings_driver_runs_prelaunch_before_snapshot() -> None:
    text = (PROJECT_ROOT / "scripts/_lib/settings-driver-claude-code.sh").read_text(encoding="utf-8")
    prelaunch = text.index('"hooks/agent-prelaunch.sh"')
    snapshot = text.index('"hooks/pre-agent-snapshot.sh"')
    assert prelaunch < snapshot
