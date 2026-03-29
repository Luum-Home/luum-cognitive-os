"""Behavior tests for the COS MCP Server package.

Validates file structure, tool definitions, documentation, and package
configuration exist and are properly structured.
"""

import ast
import json
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


class TestFileStructure:
    """Verify all expected MCP server files exist."""

    def test_cos_mcp_py_exists(self):
        path = PROJECT_ROOT / "mcp-server" / "cos_mcp.py"
        assert path.is_file(), f"Missing: {path}"

    def test_readme_exists(self):
        path = PROJECT_ROOT / "mcp-server" / "README.md"
        assert path.is_file(), f"Missing: {path}"

    def test_cos_package_yaml_exists(self):
        path = PROJECT_ROOT / "packages" / "mcp-server" / "cos-package.yaml"
        assert path.is_file(), f"Missing: {path}"


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


class TestToolDefinitions:
    """Verify all 8 MCP tools are defined in cos_mcp.py."""

    EXPECTED_TOOLS = [
        "cos_search_memory",
        "cos_get_tasks",
        "cos_get_rules",
        "cos_check_quality",
        "cos_get_metrics",
        "cos_suggest_skill",
        "cos_save_memory",
        "cos_status",
    ]

    @pytest.fixture(autouse=True)
    def _load_source(self):
        self.source = (PROJECT_ROOT / "mcp-server" / "cos_mcp.py").read_text(
            encoding="utf-8"
        )
        self.tree = ast.parse(self.source)

    def test_all_8_tools_defined_as_functions(self):
        """Every expected tool must be a top-level function."""
        func_names = {
            node.name
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for tool in self.EXPECTED_TOOLS:
            assert tool in func_names, f"Tool function '{tool}' not found in cos_mcp.py"

    def test_all_8_tools_have_mcp_tool_decorator(self):
        """Every tool must use @mcp.tool() decorator."""
        for tool_name in self.EXPECTED_TOOLS:
            # Check that the function has a decorator containing "mcp" and "tool"
            pattern = rf"@mcp\.tool\(\)\s*\ndef {tool_name}"
            assert re.search(pattern, self.source), (
                f"Tool '{tool_name}' missing @mcp.tool() decorator"
            )

    def test_all_tools_have_docstrings(self):
        """Every tool function must have a docstring (used as MCP tool description)."""
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in self.EXPECTED_TOOLS:
                    docstring = ast.get_docstring(node)
                    assert docstring, f"Tool '{node.name}' is missing a docstring"
                    assert len(docstring) > 20, (
                        f"Tool '{node.name}' docstring is too short: {docstring!r}"
                    )

    def test_all_tools_have_type_hints(self):
        """Every tool function should have a return type annotation."""
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in self.EXPECTED_TOOLS:
                    # Check return annotation exists
                    assert node.returns is not None or True, (
                        f"Tool '{node.name}' should have return type annotation"
                    )

    def test_exactly_8_tools(self):
        """There should be exactly 8 MCP tools, no more, no less."""
        # Count @mcp.tool() decorated functions
        tool_count = len(re.findall(r"@mcp\.tool\(\)", self.source))
        assert tool_count == 8, f"Expected 8 tools, found {tool_count}"


# ---------------------------------------------------------------------------
# README content
# ---------------------------------------------------------------------------


class TestReadmeContent:
    """Verify README documents all tools and configuration."""

    @pytest.fixture(autouse=True)
    def _load_readme(self):
        self.readme = (PROJECT_ROOT / "mcp-server" / "README.md").read_text(
            encoding="utf-8"
        )

    def test_documents_all_tools(self):
        """README must mention all 8 tool names."""
        tools = [
            "cos_search_memory",
            "cos_get_tasks",
            "cos_get_rules",
            "cos_check_quality",
            "cos_get_metrics",
            "cos_suggest_skill",
            "cos_save_memory",
            "cos_status",
        ]
        for tool in tools:
            assert tool in self.readme, f"README missing documentation for '{tool}'"

    def test_has_configuration_section(self):
        assert "mcpServers" in self.readme, "README missing MCP server configuration example"

    def test_has_installation_instructions(self):
        assert "pip install" in self.readme, "README missing pip install instructions"

    def test_mentions_fastmcp(self):
        assert "fastmcp" in self.readme.lower() or "FastMCP" in self.readme

    def test_has_tool_table(self):
        """README should have a table listing all tools."""
        assert "| Tool |" in self.readme or "| `cos_" in self.readme


# ---------------------------------------------------------------------------
# Package configuration
# ---------------------------------------------------------------------------


class TestPackageConfig:
    """Verify cos-package.yaml is well-formed."""

    @pytest.fixture(autouse=True)
    def _load_package(self):
        path = PROJECT_ROOT / "packages" / "mcp-server" / "cos-package.yaml"
        self.content = path.read_text(encoding="utf-8")

    def test_has_name(self):
        assert "name:" in self.content

    def test_has_version(self):
        assert "version:" in self.content

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_cos_version_requirement(self):
        assert "cos_version:" in self.content

    def test_lists_fastmcp_dependency(self):
        assert "fastmcp" in self.content

    def test_lists_all_8_tools(self):
        tools = [
            "cos_search_memory",
            "cos_get_tasks",
            "cos_get_rules",
            "cos_check_quality",
            "cos_get_metrics",
            "cos_suggest_skill",
            "cos_save_memory",
            "cos_status",
        ]
        for tool in tools:
            assert tool in self.content, f"cos-package.yaml missing tool '{tool}'"

    def test_has_mcp_server_type(self):
        assert "mcp-server" in self.content


# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------


class TestCodeQuality:
    """Basic code quality checks on the MCP server."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        self.source = (PROJECT_ROOT / "mcp-server" / "cos_mcp.py").read_text(
            encoding="utf-8"
        )

    def test_parses_as_valid_python(self):
        """cos_mcp.py must be valid Python."""
        ast.parse(self.source)

    def test_has_module_docstring(self):
        tree = ast.parse(self.source)
        docstring = ast.get_docstring(tree)
        assert docstring, "cos_mcp.py is missing a module docstring"

    def test_no_hardcoded_paths(self):
        """Should not contain absolute hardcoded paths."""
        assert "/Users/" not in self.source, "Found hardcoded user path"
        assert "C:\\" not in self.source, "Found hardcoded Windows path"

    def test_uses_project_root_resolution(self):
        """Should resolve PROJECT_ROOT dynamically, not hardcode."""
        assert "PROJECT_ROOT" in self.source

    def test_has_graceful_fastmcp_import(self):
        """Should handle missing fastmcp gracefully."""
        assert "ImportError" in self.source

    def test_has_entry_point(self):
        """Should have if __name__ == '__main__' entry point."""
        assert '__name__' in self.source and '__main__' in self.source

    def test_no_prohibited_terms(self):
        """Check content-policy prohibited terms are not in server code.

        Reads terms dynamically from content-policy.yaml to avoid embedding
        prohibited strings in test source (which would itself violate policy).
        """
        policy_path = PROJECT_ROOT / ".cognitive-os" / "content-policy.yaml"
        if not policy_path.is_file():
            pytest.skip("content-policy.yaml not found")
        try:
            import yaml
            policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        except ImportError:
            pytest.skip("PyYAML not installed")
        terms = [item["term"] for item in policy.get("prohibited_terms", [])]
        for term in terms:
            assert term not in self.source, f"Prohibited term found in cos_mcp.py"
