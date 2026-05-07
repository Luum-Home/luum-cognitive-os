from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml


EXPECTED_TOOLS = {
    "cos_search_memory",
    "cos_get_tasks",
    "cos_get_rules",
    "cos_check_quality",
    "cos_get_metrics",
    "cos_suggest_skill",
    "cos_save_memory",
    "cos_status",
}


@pytest.mark.audit
def test_mcp_package_export_resolves_to_canonical_server(project_root: Path) -> None:
    package_server = project_root / "packages" / "mcp-server" / "cos_mcp.py"
    canonical = project_root / "mcp-server" / "cos_mcp.py"

    assert package_server.exists()
    assert package_server.resolve() == canonical.resolve()


@pytest.mark.audit
def test_mcp_package_manifest_matches_server_tools(project_root: Path) -> None:
    manifest = yaml.safe_load((project_root / "packages" / "mcp-server" / "cos-package.yaml").read_text())
    manifest_tools = {tool["name"] for tool in manifest["tools"]}
    assert manifest["exports"][0]["source"] == "cos_mcp.py"
    assert manifest_tools == EXPECTED_TOOLS

    module = ast.parse((project_root / "mcp-server" / "cos_mcp.py").read_text())
    defined = {node.name for node in module.body if isinstance(node, ast.FunctionDef) and node.name.startswith("cos_")}
    assert EXPECTED_TOOLS <= defined
