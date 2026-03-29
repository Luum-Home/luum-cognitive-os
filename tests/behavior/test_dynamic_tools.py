"""Behavior tests for dynamic tool creation feature.

Verifies that the rule file, directory conventions, and integration
points are correctly set up in the Cognitive OS project structure.
"""

import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestRuleFileExists:
    def test_dynamic_tool_creation_rule_exists(self):
        rule_path = PROJECT_ROOT / "rules" / "dynamic-tool-creation.md"
        assert rule_path.is_file(), "rules/dynamic-tool-creation.md must exist"

    def test_rule_has_contextual_trigger(self):
        rule_path = PROJECT_ROOT / "rules" / "dynamic-tool-creation.md"
        content = rule_path.read_text()
        assert "Contextual Trigger" in content, (
            "Rule must have a Contextual Trigger section for contextual loading"
        )

    def test_rule_references_library(self):
        rule_path = PROJECT_ROOT / "rules" / "dynamic-tool-creation.md"
        content = rule_path.read_text()
        assert "DynamicToolCreator" in content, (
            "Rule must reference the DynamicToolCreator library"
        )

    def test_rule_documents_safety_boundaries(self):
        rule_path = PROJECT_ROOT / "rules" / "dynamic-tool-creation.md"
        content = rule_path.read_text()
        assert "Safety Boundaries" in content or "safety" in content.lower(), (
            "Rule must document safety boundaries for dynamic tool creation"
        )


class TestDynamicToolsDirectory:
    def test_dynamic_tools_dir_convention(self):
        """The .cognitive-os/dynamic-tools/ path is the documented convention."""
        rule_path = PROJECT_ROOT / "rules" / "dynamic-tool-creation.md"
        content = rule_path.read_text()
        assert ".cognitive-os/dynamic-tools" in content, (
            "Rule must document .cognitive-os/dynamic-tools/ as the tool directory"
        )

    def test_cognitive_os_is_gitignored(self):
        """The .cognitive-os/ directory should be gitignored (session-scoped)."""
        gitignore = (PROJECT_ROOT / ".gitignore").read_text()
        assert ".cognitive-os/" in gitignore, (
            ".cognitive-os/ must be in .gitignore so dynamic tools are session-scoped"
        )


class TestLibraryExists:
    def test_dynamic_tool_creator_module(self):
        lib_path = PROJECT_ROOT / "lib" / "dynamic_tool_creator.py"
        assert lib_path.is_file(), "lib/dynamic_tool_creator.py must exist"

    def test_module_has_class(self):
        lib_path = PROJECT_ROOT / "lib" / "dynamic_tool_creator.py"
        content = lib_path.read_text()
        assert "class DynamicToolCreator" in content

    def test_module_has_create_tool(self):
        lib_path = PROJECT_ROOT / "lib" / "dynamic_tool_creator.py"
        content = lib_path.read_text()
        assert "def create_tool" in content

    def test_module_has_promote_to_skill(self):
        lib_path = PROJECT_ROOT / "lib" / "dynamic_tool_creator.py"
        content = lib_path.read_text()
        assert "def promote_to_skill" in content

    def test_module_has_cleanup(self):
        lib_path = PROJECT_ROOT / "lib" / "dynamic_tool_creator.py"
        content = lib_path.read_text()
        assert "def cleanup_session_tools" in content

    def test_module_has_list(self):
        lib_path = PROJECT_ROOT / "lib" / "dynamic_tool_creator.py"
        content = lib_path.read_text()
        assert "def list_dynamic_tools" in content


class TestIntegrationWithExistingSystems:
    def test_rule_references_auto_skill_generation(self):
        """Dynamic tools should reference the existing auto-skill-generation system."""
        rule_path = PROJECT_ROOT / "rules" / "dynamic-tool-creation.md"
        content = rule_path.read_text()
        assert "auto-skill-generation" in content.lower() or "Auto-Skill Generation" in content, (
            "Rule must reference auto-skill-generation for context on how it differs"
        )

    def test_rule_references_agent_security(self):
        """Dynamic tools must respect agent security boundaries."""
        rule_path = PROJECT_ROOT / "rules" / "dynamic-tool-creation.md"
        content = rule_path.read_text()
        assert "agent-security" in content.lower() or "Agent Security" in content, (
            "Rule must reference agent-security for safety integration"
        )

    def test_skill_creator_skill_exists(self):
        """The skill-creator skill should exist for promotion workflow."""
        skill_path = PROJECT_ROOT / "skills" / "skill-creator" / "SKILL.md"
        assert skill_path.is_file(), (
            "skills/skill-creator/SKILL.md must exist (used by promote workflow)"
        )

    def test_auto_skill_generation_rule_exists(self):
        """The post-hoc auto-skill-generation rule must exist alongside dynamic tools."""
        # Could be in rules/ or packages/
        rule_in_rules = PROJECT_ROOT / "rules" / "auto-skill-generation.md"
        rule_in_packages = PROJECT_ROOT / "packages" / "skill-governance" / "rules" / "auto-skill-generation.md"
        assert rule_in_rules.is_file() or rule_in_packages.is_file(), (
            "auto-skill-generation.md must exist (complementary to dynamic tools)"
        )


class TestToolTypes:
    def test_rule_documents_bash_type(self):
        rule_path = PROJECT_ROOT / "rules" / "dynamic-tool-creation.md"
        content = rule_path.read_text()
        assert "bash" in content.lower()

    def test_rule_documents_python_type(self):
        rule_path = PROJECT_ROOT / "rules" / "dynamic-tool-creation.md"
        content = rule_path.read_text()
        assert "python" in content.lower()

    def test_rule_documents_skill_type(self):
        rule_path = PROJECT_ROOT / "rules" / "dynamic-tool-creation.md"
        content = rule_path.read_text()
        assert "skill" in content.lower()
