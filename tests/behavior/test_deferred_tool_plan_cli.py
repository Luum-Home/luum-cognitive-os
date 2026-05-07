from __future__ import annotations

import json
import subprocess

import pytest


@pytest.mark.behavior
def test_deferred_tool_plan_cli_outputs_plan_and_index(project_root) -> None:
    plan = subprocess.run(
        [str(project_root / "scripts" / "cos-deferred-tool-plan"), "--project-dir", str(project_root), "--estimated-tool-tokens", "20000"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(plan.stdout)["status"] == "deferred"

    index = subprocess.run(
        [str(project_root / "scripts" / "cos-deferred-tool-plan"), "--project-dir", str(project_root), "--index"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(index.stdout)["tools"]
