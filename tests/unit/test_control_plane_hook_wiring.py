from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_control_plane_hook_fast_wired_before_agent_prelaunch() -> None:
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    agent_group = next(item for item in settings["hooks"]["PreToolUse"] if item.get("matcher") == "Agent")
    commands = [hook.get("command", "") for hook in agent_group["hooks"]]

    control_idx = next(i for i, cmd in enumerate(commands) if "hooks/control-plane-audit.sh" in cmd)
    prelaunch_idx = next(i for i, cmd in enumerate(commands) if "hooks/agent-prelaunch.sh" in cmd)

    assert control_idx < prelaunch_idx


def test_control_plane_hook_script_exists_and_is_executable() -> None:
    hook = ROOT / "hooks" / "control-plane-audit.sh"
    assert hook.exists()
    assert hook.stat().st_mode & 0o111
