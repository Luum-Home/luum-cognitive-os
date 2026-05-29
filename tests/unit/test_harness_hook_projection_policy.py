"""Anti-drift tests for declarative harness hook projection policy."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "manifests" / "harness-hook-projection-policy.yaml"
DRIVER = ROOT / "scripts" / "_lib" / "settings-driver-claude-code.sh"
CLI = ROOT / "scripts" / "cos-harness-projection-policy"


def _driver_settings(profile: str) -> dict:
    env = os.environ.copy()
    env.update({"PROJECT_DIR": str(ROOT), "PROFILE": profile})
    result = subprocess.run(
        ["bash", str(DRIVER), "--emit"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _bash_scripts(settings: dict) -> list[str]:
    groups = settings["hooks"]["PreToolUse"]
    bash_group = next(group for group in groups if group.get("matcher") == "Bash")
    scripts: list[str] = []
    for hook in bash_group["hooks"]:
        matches = re.findall(r'\$CLAUDE_PROJECT_DIR/([^" ]+\.sh)', hook["command"])
        assert matches, hook
        scripts.append(matches[-1])
    return scripts


def _policy_scripts(profile: str) -> list[str]:
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    spec = policy["harnesses"]["claude-code"]["profiles"][profile]
    if "alias_of" in spec:
        spec = policy["harnesses"]["claude-code"]["profiles"][spec["alias_of"]]
    hook = next(h for h in spec["hooks"] if h["event"] == "PreToolUse" and h["matcher"] == "Bash")
    return hook["scripts"]


def test_default_bash_hot_path_matches_projection_policy() -> None:
    assert _bash_scripts(_driver_settings("default")) == _policy_scripts("default")


def test_full_bash_mesh_matches_projection_policy() -> None:
    assert _bash_scripts(_driver_settings("full")) == _policy_scripts("full")


def test_projection_policy_cli_outputs_machine_readable_scripts() -> None:
    result = subprocess.run(
        [str(CLI), "--harness", "claude-code", "--profile", "default", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["scripts"] == ["hooks/bash-hot-path-dispatcher.sh"]
