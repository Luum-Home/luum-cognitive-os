from __future__ import annotations

import json
import subprocess
from pathlib import Path

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



@pytest.mark.behavior
def test_deferred_tool_plan_cli_list_changed_and_native_payload(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "manifests").mkdir(parents=True)
    (project / "manifests/deferred-tool-loading.yaml").write_text(
        "schema_version: deferred-tool-loading/v1\n"
        "tools:\n  - name: alpha\n    load_mode: deferred\n"
    )
    root = Path(__file__).resolve().parent.parent.parent
    changed = subprocess.run(
        [str(root / "scripts/cos-deferred-tool-plan"), "--project-dir", str(project), "--list-changed", "--update-state"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert changed.returncode == 0
    assert json.loads(changed.stdout)["added_tools"] == ["alpha"]
    native = subprocess.run(
        [str(root / "scripts/cos-deferred-tool-plan"), "--project-dir", str(project), "--native-payload-provider", "claude"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert native.returncode == 0
    assert json.loads(native.stdout)["native_defer_loading_supported"] is False
