from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.mark.audit
def test_branch_per_task_manifest_observe_mode(project_root: Path) -> None:
    manifest = yaml.safe_load((project_root / "manifests" / "branch-per-task.yaml").read_text())

    assert manifest["schema_version"] == "branch-per-task/v1"
    assert manifest["policy"]["default_mode"] == "observe"
    assert manifest["policy"]["branch_prefix"] == "codex/task"
    assert "read_only_agents_are_exempt" in manifest["invariants"]
