from __future__ import annotations

import json
import subprocess

import pytest


@pytest.mark.behavior
def test_policy_settings_projection_lists_real_policy_hooks(project_root) -> None:
    proc = subprocess.run(
        [str(project_root / "scripts" / "cos-policy-settings-projection"), "--project-dir", str(project_root), "--host", "claude-code", "--json"],
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    ids = {entry["policy_id"] for entry in payload["entries"]}
    assert {"destructive-bash", "destructive-git", "protected-config-write"} <= ids
    for entry in payload["entries"]:
        assert entry["event"] == "PreToolUse"
        assert "cos-policy-eval" in entry["command"]
        assert entry["mode"] == "projected-plan-only"
