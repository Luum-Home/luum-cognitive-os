"""Tests for the multi-IDE compatibility system.

Validates that IDE compatibility documentation exists, covers all supported IDEs,
and that the ide-bridge.sh script is properly structured.
"""

from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestIdeCompatibilityDoc:
    """Tests for the ide-compatibility.md documentation."""

    def test_ide_compatibility_doc_exists(self):
        """docs/ide-compatibility.md must exist."""
        doc = PROJECT_ROOT / "docs" / "ide-compatibility.md"
        assert doc.exists(), "docs/ide-compatibility.md not found"

    def test_documents_claude_code_support(self):
        """ide-compatibility.md must document Claude Code support."""
        doc = PROJECT_ROOT / "docs" / "ide-compatibility.md"
        content = doc.read_text()
        assert (
            "Claude Code" in content
        ), "ide-compatibility.md must document Claude Code support"
        assert (
            "Full" in content
        ), "Claude Code should have Full support level documented"

    def test_documents_cursor_support(self):
        """ide-compatibility.md must document Cursor support."""
        doc = PROJECT_ROOT / "docs" / "ide-compatibility.md"
        content = doc.read_text()
        assert (
            "Cursor" in content
        ), "ide-compatibility.md must document Cursor support"

    def test_documents_windsurf_support(self):
        """ide-compatibility.md must document Windsurf support."""
        doc = PROJECT_ROOT / "docs" / "ide-compatibility.md"
        content = doc.read_text()
        assert (
            "Windsurf" in content
        ), "ide-compatibility.md must document Windsurf support"

    def test_documents_aider_support(self):
        """ide-compatibility.md must document Aider support."""
        doc = PROJECT_ROOT / "docs" / "ide-compatibility.md"
        content = doc.read_text()
        assert (
            "Aider" in content
        ), "ide-compatibility.md must document Aider support"

    def test_limitations_documented_for_non_claude_code(self):
        """Non-Claude-Code IDEs must have limitations documented."""
        doc = PROJECT_ROOT / "docs" / "ide-compatibility.md"
        content = doc.read_text().lower()
        # Must mention that hooks don't work in other IDEs
        assert (
            "no hooks" in content or "none" in content
        ), "Limitations for non-Claude-Code IDEs must be documented"
        # Must mention that safety mesh is not available
        assert (
            "safety mesh" in content
        ), "Missing safety mesh limitation documentation"

    def test_support_matrix_table_exists(self):
        """ide-compatibility.md must contain a support matrix table."""
        doc = PROJECT_ROOT / "docs" / "ide-compatibility.md"
        content = doc.read_text()
        # Check for table headers that indicate a support matrix
        assert (
            "Support Level" in content or "Support Matrix" in content
            or "Summary Matrix" in content or "Compatibility Levels" in content
        ), "ide-compatibility.md must contain a support matrix"


class TestIdeBridgeScript:
    """Tests for the ide-bridge.sh script."""

    def test_ide_bridge_script_exists(self):
        """scripts/ide-bridge.sh must exist."""
        script = PROJECT_ROOT / "scripts" / "ide-bridge.sh"
        assert script.exists(), "scripts/ide-bridge.sh not found"

    def test_ide_bridge_has_shebang(self):
        """scripts/ide-bridge.sh must have a proper shebang."""
        script = PROJECT_ROOT / "scripts" / "ide-bridge.sh"
        content = script.read_text()
        assert content.startswith("#!/"), "scripts/ide-bridge.sh missing shebang"

    def test_ide_bridge_supports_cursor(self):
        """ide-bridge.sh must support the 'cursor' flag."""
        script = PROJECT_ROOT / "scripts" / "ide-bridge.sh"
        content = script.read_text()
        assert "cursor" in content, "ide-bridge.sh must support cursor flag"

    def test_ide_bridge_supports_windsurf(self):
        """ide-bridge.sh must support the 'windsurf' flag."""
        script = PROJECT_ROOT / "scripts" / "ide-bridge.sh"
        content = script.read_text()
        assert "windsurf" in content, "ide-bridge.sh must support windsurf flag"

    def test_ide_bridge_supports_aider(self):
        """ide-bridge.sh must support the 'aider' flag."""
        script = PROJECT_ROOT / "scripts" / "ide-bridge.sh"
        content = script.read_text()
        assert "aider" in content, "ide-bridge.sh must support aider flag"

    def test_ide_bridge_documents_limitations(self):
        """ide-bridge.sh should document that hooks only work with Claude Code."""
        script = PROJECT_ROOT / "scripts" / "ide-bridge.sh"
        content = script.read_text()
        assert (
            "hooks" in content.lower() and "claude code" in content.lower()
        ), "ide-bridge.sh should document hook limitations"


class TestGettingStartedIdeSection:
    """Tests for the IDE section in getting-started.md."""

    def test_getting_started_has_ide_section(self):
        """getting-started.md must have a section about other IDEs."""
        doc = PROJECT_ROOT / "docs" / "getting-started.md"
        content = doc.read_text()
        assert (
            "Other IDE" in content or "other IDE" in content
        ), "getting-started.md must have a section about using with other IDEs"

    def test_getting_started_references_ide_bridge(self):
        """getting-started.md must reference ide-bridge.sh."""
        doc = PROJECT_ROOT / "docs" / "getting-started.md"
        content = doc.read_text()
        assert (
            "ide-bridge" in content
        ), "getting-started.md must reference ide-bridge.sh"
