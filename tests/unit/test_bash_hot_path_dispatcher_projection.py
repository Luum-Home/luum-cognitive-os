# SCOPE: os-only
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / "scripts" / "_lib" / "settings-driver-claude-code.sh"


def emit_settings(profile: str = "default") -> dict:
    env = os.environ.copy()
    env["PROJECT_DIR"] = str(ROOT)
    env["PROFILE"] = profile
    out = subprocess.check_output(["bash", str(DRIVER), "--emit"], env=env, text=True)
    return json.loads(out)


def bash_group(settings: dict) -> list[str]:
    for group in settings["hooks"]["PreToolUse"]:
        if group.get("matcher") == "Bash":
            return [hook["command"] for hook in group["hooks"]]
    raise AssertionError("PreToolUse Bash group not found")


def test_default_bash_hot_path_uses_tier_dispatcher_only() -> None:
    commands = bash_group(emit_settings())

    assert len(commands) == 1
    assert "hooks/bash-hot-path-dispatcher.sh" in commands[0]
    assert "hooks/destructive-git-blocker.sh" not in commands[0]
    assert "hooks/scope-marker-portability-gate.sh" not in commands[0]


def test_full_profile_keeps_exhaustive_bash_mesh() -> None:
    commands = "\n".join(bash_group(emit_settings("full")))

    assert "hooks/destructive-git-blocker.sh" in commands
    assert "hooks/scope-marker-portability-gate.sh" in commands
    assert "hooks/bash-hot-path-dispatcher.sh" not in commands
