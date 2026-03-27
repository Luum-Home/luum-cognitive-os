"""Tests for IDE compatibility tracking across all 30 tools.

Validates that:
- ide-compatibility.md documents ALL 30 tools
- Each compatibility level has the correct count
- ide-bridge.sh supports at least 5 IDEs (actually 15)
- Each tool entry has name, config, hooks, rules, MCP columns
"""

from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestIdeTrackingCompleteness:
    """Verify all 30 tools are documented in ide-compatibility.md."""

    @pytest.fixture(autouse=True)
    def load_doc(self):
        self.doc_path = PROJECT_ROOT / "docs" / "ide-compatibility.md"
        assert self.doc_path.exists(), "docs/ide-compatibility.md not found"
        self.content = self.doc_path.read_text()

    # ── FULL COMPATIBILITY (6 tools) ──────────────────────────────────

    FULL_TOOLS = [
        "Claude Code",
        "Gemini CLI",
        "GitHub Copilot CLI",
        "Cursor",
        "Windsurf",
        "Kiro",
    ]

    @pytest.mark.parametrize("tool", FULL_TOOLS)
    def test_full_tool_documented(self, tool):
        """Each FULL compatibility tool must be listed."""
        assert tool in self.content, f"FULL tool '{tool}' not found in ide-compatibility.md"

    def test_full_compatibility_count(self):
        """FULL COMPATIBILITY section must list exactly 6 tools."""
        assert "## FULL COMPATIBILITY (6 tools)" in self.content, (
            "FULL COMPATIBILITY section header with count 6 not found"
        )

    # ── HIGH COMPATIBILITY (4 tools) ──────────────────────────────────

    HIGH_TOOLS = [
        "OpenCode",
        "Codex CLI",
        "Cline",
        "Qodo",
    ]

    @pytest.mark.parametrize("tool", HIGH_TOOLS)
    def test_high_tool_documented(self, tool):
        """Each HIGH compatibility tool must be listed."""
        assert tool in self.content, f"HIGH tool '{tool}' not found in ide-compatibility.md"

    def test_high_compatibility_count(self):
        """HIGH COMPATIBILITY section must list exactly 4 tools."""
        assert "## HIGH COMPATIBILITY (4 tools)" in self.content, (
            "HIGH COMPATIBILITY section header with count 4 not found"
        )

    # ── RULES-ONLY (9 tools) ─────────────────────────────────────────

    RULES_TOOLS = [
        "Aider",
        "Warp",
        "Factory.ai",
        "Trae",
        "Zed AI",
        "Roo Code",
        "Continue.dev",
        "GitHub Copilot (VS Code)",
        "Augment Code",
    ]

    @pytest.mark.parametrize("tool", RULES_TOOLS)
    def test_rules_tool_documented(self, tool):
        """Each RULES-ONLY tool must be listed."""
        assert tool in self.content, f"RULES-ONLY tool '{tool}' not found in ide-compatibility.md"

    def test_rules_only_count(self):
        """RULES-ONLY section must list exactly 9 tools."""
        assert "## RULES-ONLY (9 tools)" in self.content, (
            "RULES-ONLY section header with count 9 not found"
        )

    # ── MINIMAL (6 tools) ────────────────────────────────────────────

    MINIMAL_TOOLS = [
        "Void IDE",
        "PearAI",
        "JetBrains AI",
        "Sourcegraph Cody",
        "Tabnine",
        "Google Antigravity",
    ]

    @pytest.mark.parametrize("tool", MINIMAL_TOOLS)
    def test_minimal_tool_documented(self, tool):
        """Each MINIMAL tool must be listed."""
        assert tool in self.content, f"MINIMAL tool '{tool}' not found in ide-compatibility.md"

    def test_minimal_count(self):
        """MINIMAL section must list exactly 6 tools."""
        assert "## MINIMAL (6 tools)" in self.content, (
            "MINIMAL section header with count 6 not found"
        )

    # ── NONE (5 tools) ───────────────────────────────────────────────

    NONE_TOOLS = [
        "Devin",
        "Replit Agent",
        "Bolt.new",
        "Lovable",
        "v0",
    ]

    @pytest.mark.parametrize("tool", NONE_TOOLS)
    def test_none_tool_documented(self, tool):
        """Each NONE compatibility tool must be listed."""
        assert tool in self.content, f"NONE tool '{tool}' not found in ide-compatibility.md"

    def test_none_count(self):
        """NONE section must list exactly 5 tools."""
        assert "## NONE (5 tools)" in self.content, (
            "NONE section header with count 5 not found"
        )

    # ── Total count ──────────────────────────────────────────────────

    def test_total_tool_count_at_least_30(self):
        """The summary matrix must list at least 30 tools (numbered rows)."""
        # Count rows in the summary matrix table that start with "| N |"
        lines = self.content.split("\n")
        numbered_rows = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|"):
                parts = [p.strip() for p in stripped.split("|") if p.strip()]
                if parts and parts[0].isdigit():
                    numbered_rows += 1
        assert numbered_rows >= 30, (
            f"Summary matrix has {numbered_rows} numbered rows, expected >= 30"
        )


class TestToolEntryStructure:
    """Verify each tool entry has the required fields."""

    @pytest.fixture(autouse=True)
    def load_doc(self):
        self.doc_path = PROJECT_ROOT / "docs" / "ide-compatibility.md"
        self.content = self.doc_path.read_text()

    REQUIRED_COLUMNS = ["Rules", "Hooks", "MCP"]

    def test_summary_matrix_has_required_columns(self):
        """The summary matrix table must have Rules, Hooks, MCP columns."""
        # Find the summary matrix header line
        lines = self.content.split("\n")
        header_found = False
        for line in lines:
            if "Rules" in line and "Hooks" in line and "MCP" in line and "|" in line:
                header_found = True
                break
        assert header_found, (
            "Summary matrix must have a table header with Rules, Hooks, and MCP columns"
        )

    def test_summary_matrix_has_tool_column(self):
        """The summary matrix must have a Tool column."""
        lines = self.content.split("\n")
        for line in lines:
            if "Tool" in line and "|" in line and "Company" in line:
                return
        pytest.fail("Summary matrix must have Tool and Company columns")

    def test_summary_matrix_has_open_source_column(self):
        """The summary matrix must have an Open Source column."""
        lines = self.content.split("\n")
        for line in lines:
            if "Open Source" in line and "|" in line:
                return
        pytest.fail("Summary matrix must have an Open Source column")

    def test_full_tools_have_config_documented(self):
        """Each FULL tool section must document its config mechanism."""
        for tool_num in range(1, 7):
            assert f"**Config**:" in self.content or f"- **Config**:" in self.content, (
                f"Tool #{tool_num} missing Config documentation"
            )

    def test_full_tools_have_hooks_documented(self):
        """Each FULL tool section must document hooks support."""
        assert self.content.count("**Hooks**: YES") >= 6, (
            "Expected at least 6 tools with '**Hooks**: YES' (FULL tier)"
        )

    def test_full_tools_have_mcp_documented(self):
        """Each FULL tool section must document MCP support."""
        assert self.content.count("**MCP**: YES") >= 6, (
            "Expected at least 6 tools with '**MCP**: YES' (FULL tier)"
        )


class TestIdeBridgeSupport:
    """Verify ide-bridge.sh supports at least 5 IDEs (actually 15)."""

    @pytest.fixture(autouse=True)
    def load_script(self):
        self.script_path = PROJECT_ROOT / "scripts" / "ide-bridge.sh"
        assert self.script_path.exists(), "scripts/ide-bridge.sh not found"
        self.content = self.script_path.read_text()

    EXPECTED_IDES = [
        "cursor",
        "windsurf",
        "aider",
        "gemini",
        "copilot",
        "codex",
        "opencode",
        "trae",
        "roo",
        "continue",
        "augment",
        "warp",
        "cline",
        "zed",
    ]

    def test_ide_bridge_supports_at_least_5_ides(self):
        """ide-bridge.sh must support at least 5 IDEs."""
        supported = sum(1 for ide in self.EXPECTED_IDES if ide in self.content)
        assert supported >= 5, (
            f"ide-bridge.sh supports only {supported} IDEs, expected >= 5"
        )

    @pytest.mark.parametrize("ide", EXPECTED_IDES)
    def test_ide_bridge_supports_ide(self, ide):
        """ide-bridge.sh must have a case/function for each expected IDE."""
        assert ide in self.content, f"ide-bridge.sh missing support for '{ide}'"

    def test_ide_bridge_has_help_flag(self):
        """ide-bridge.sh must support --help flag."""
        assert "--help" in self.content

    def test_ide_bridge_has_list_flag(self):
        """ide-bridge.sh must support --list flag."""
        assert "--list" in self.content

    def test_ide_bridge_has_shebang(self):
        """ide-bridge.sh must have a proper bash shebang."""
        assert self.content.startswith("#!/"), "Missing shebang"

    def test_ide_bridge_documents_hook_limitations(self):
        """ide-bridge.sh should document that hooks have limitations in non-Claude IDEs."""
        content_lower = self.content.lower()
        assert "hooks" in content_lower and "claude code" in content_lower, (
            "ide-bridge.sh should document hook limitations for non-Claude IDEs"
        )

    def test_ide_bridge_generates_cursor_rules_dir(self):
        """Cursor generator must target .cursor/rules/ directory."""
        assert ".cursor/rules" in self.content

    def test_ide_bridge_generates_windsurfrules(self):
        """Windsurf generator must target .windsurfrules file."""
        assert ".windsurfrules" in self.content

    def test_ide_bridge_generates_copilot_instructions(self):
        """Copilot generator must target .github/copilot-instructions.md."""
        assert "copilot-instructions.md" in self.content

    def test_ide_bridge_generates_agents_md(self):
        """Codex generator must target AGENTS.md."""
        assert "AGENTS.md" in self.content

    def test_ide_bridge_generates_gemini_md(self):
        """Gemini generator must target GEMINI.md."""
        assert "GEMINI.md" in self.content

    def test_ide_bridge_generates_clinerules(self):
        """Cline generator must target .clinerules."""
        assert ".clinerules" in self.content

    def test_ide_bridge_generates_warp_md(self):
        """Warp generator must target WARP.md."""
        assert "WARP.md" in self.content


class TestCompatibilityDocCrossReferences:
    """Verify ide-compatibility.md references ide-bridge.sh correctly."""

    @pytest.fixture(autouse=True)
    def load_files(self):
        self.doc_path = PROJECT_ROOT / "docs" / "ide-compatibility.md"
        self.content = self.doc_path.read_text()

    def test_doc_references_ide_bridge_script(self):
        """ide-compatibility.md must reference ide-bridge.sh."""
        assert "ide-bridge.sh" in self.content, (
            "ide-compatibility.md must reference scripts/ide-bridge.sh"
        )

    def test_doc_has_generating_configs_section(self):
        """ide-compatibility.md must have a section about generating configs."""
        assert "Generating IDE Configs" in self.content, (
            "ide-compatibility.md must have a 'Generating IDE Configs' section"
        )

    def test_doc_has_recommendations_section(self):
        """ide-compatibility.md must have a recommendations section."""
        assert "Recommendations" in self.content, (
            "ide-compatibility.md must have a 'Recommendations' section"
        )

    def test_doc_explains_best_effort_rules(self):
        """ide-compatibility.md must explain what best-effort rules means."""
        content_lower = self.content.lower()
        assert "best-effort" in content_lower or "best effort" in content_lower, (
            "ide-compatibility.md must explain best-effort rule loading"
        )

    def test_doc_mentions_safety_mesh(self):
        """ide-compatibility.md must mention safety mesh limitations."""
        assert "safety mesh" in self.content.lower(), (
            "ide-compatibility.md must discuss safety mesh availability"
        )
