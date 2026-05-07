from __future__ import annotations

import pytest

from lib.deferred_tool_loading import plan_tool_loading, toolsearch_index


@pytest.mark.unit
def test_below_threshold_keeps_tools_visible(project_root) -> None:
    plan = plan_tool_loading(project_root, estimated_tool_tokens=100)
    assert plan.status == "eager"
    assert plan.deferred_tools == []
    assert "cos_tool_discovery_preuse" in plan.visible_tools


@pytest.mark.unit
def test_above_threshold_defers_non_eager_tools(project_root) -> None:
    plan = plan_tool_loading(project_root, estimated_tool_tokens=20_000)
    assert plan.status == "deferred"
    assert plan.toolsearch_enabled is True
    assert "cos_tool_discovery_preuse" in plan.visible_tools
    assert "cos_mcp_server_surface" in plan.deferred_tools


@pytest.mark.unit
def test_toolsearch_index_contains_metadata(project_root) -> None:
    index = toolsearch_index(project_root)
    names = {tool["name"] for tool in index["tools"]}
    assert "cos_sandbox_adapter" in names
