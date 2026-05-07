from __future__ import annotations

from pathlib import Path

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



@pytest.mark.unit
def test_list_changed_tracks_tool_index_hash(tmp_path: Path) -> None:
    (tmp_path / "manifests").mkdir()
    manifest = tmp_path / "manifests/deferred-tool-loading.yaml"
    manifest.write_text(
        "schema_version: deferred-tool-loading/v1\n"
        "tools:\n  - name: alpha\n    load_mode: deferred\n"
    )
    from lib.deferred_tool_loading import list_changed

    first = list_changed(tmp_path, update_state=True)
    assert first["changed"] is True
    assert first["added_tools"] == ["alpha"]
    second = list_changed(tmp_path)
    assert second["changed"] is False
    manifest.write_text(
        "schema_version: deferred-tool-loading/v1\n"
        "tools:\n  - name: alpha\n    load_mode: deferred\n  - name: beta\n    load_mode: deferred\n"
    )
    third = list_changed(tmp_path)
    assert third["changed"] is True
    assert third["added_tools"] == ["beta"]



@pytest.mark.unit
def test_provider_native_payload_is_truthful_until_provider_api_exists(tmp_path: Path) -> None:
    from lib.deferred_tool_loading import provider_native_defer_payload

    payload = provider_native_defer_payload(tmp_path, provider="claude")
    assert payload["native_defer_loading_supported"] is False
    assert payload["reason"] == "provider_api_not_available"
    assert payload["toolsearch_index"]["schema_version"] == "deferred-tool-loading/v1"


def test_provider_native_payload_can_be_enabled_by_operator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lib.deferred_tool_loading import provider_native_defer_payload

    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests/deferred-tool-loading.yaml").write_text(
        "schema_version: deferred-tool-loading/v1\n"
        "tools:\n  - name: heavy\n    load_mode: deferred\n    description: Heavy tool\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("COS_NATIVE_DEFER_LOADING_PROVIDERS", "claude")

    payload = provider_native_defer_payload(tmp_path, provider="claude")

    assert payload["native_defer_loading_supported"] is True
    assert payload["provider_payload"]["defer_loading"] is True
    assert payload["provider_payload"]["list_changed"] is True
