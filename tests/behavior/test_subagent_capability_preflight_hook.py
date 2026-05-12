import subprocess

import pytest


@pytest.mark.behavior
def test_subagent_capability_hook_blocks_explore_artifact_launch(project_root):
    payload = '{"tool_name":"Agent","tool_input":{"subagent_type":"Explore","prompt":"Research and write docs/06-Daily/reports/output.md"}}'
    result = subprocess.run(
        ["bash", str(project_root / "hooks" / "subagent-capability-preflight.sh")],
        input=payload,
        capture_output=True,
        text=True,
        env={"COGNITIVE_OS_PROJECT_DIR": str(project_root)},
        timeout=10,
    )

    assert result.returncode == 2
    assert "ADR-203 SUBAGENT CAPABILITY BLOCK" in result.stderr
    assert "general-purpose" in result.stderr


@pytest.mark.behavior
def test_subagent_capability_hook_allows_parent_persistence(project_root):
    payload = '{"tool_name":"Agent","tool_input":{"subagent_type":"Explore","prompt":"Research read-only and return result only; parent will persist docs/06-Daily/reports/output.md"}}'
    result = subprocess.run(
        ["bash", str(project_root / "hooks" / "subagent-capability-preflight.sh")],
        input=payload,
        capture_output=True,
        text=True,
        env={"COGNITIVE_OS_PROJECT_DIR": str(project_root)},
        timeout=10,
    )

    assert result.returncode == 0
    assert result.stderr == ""
