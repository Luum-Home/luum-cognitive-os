from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


def _agent_hook_order(settings: dict) -> list[str]:
    for group in settings["hooks"]["PreToolUse"]:
        if group.get("matcher") == "Agent":
            return [Path(hook["command"].split()[-1].strip('"')).name for hook in group.get("hooks", [])]
    return []


@pytest.mark.audit
def test_pre_agent_two_phase_ordering(project_root: Path) -> None:
    settings = json.loads((project_root / ".claude" / "settings.json").read_text())
    order = _agent_hook_order(settings)

    assert order.index("agent-prelaunch.sh") < order.index("pre-agent-snapshot.sh")
    assert order.index("pre-agent-snapshot.sh") < order.index("agent-launch-confirmed.sh")
    assert order[-1] == "agent-launch-confirmed.sh"


@pytest.mark.audit
def test_pre_agent_snapshot_manifest_declares_two_phase(project_root: Path) -> None:
    manifest = yaml.safe_load((project_root / "manifests" / "pre-agent-snapshot.yaml").read_text())

    assert manifest["schema_version"] == "pre-agent-snapshot/v2"
    assert manifest["phases"]["plan"]["git_state_mutates"] is False
    assert manifest["phases"]["commit"]["requires_plan"] is True
    assert "phase_1_must_not_call_git_stash" in manifest["invariants"]
