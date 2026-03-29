"""Behavior tests for the reverse-engineer skill."""

import re
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestReverseEngineerSkillExists:
    """Verify the reverse-engineer skill is properly set up."""

    def test_skill_directory_exists(self) -> None:
        """Skill directory exists at skills/reverse-engineer/."""
        skill_dir = PROJECT_ROOT / "skills" / "reverse-engineer"
        assert skill_dir.is_dir(), f"Missing skill directory: {skill_dir}"

    def test_skill_md_exists(self) -> None:
        """SKILL.md exists in the skill directory."""
        skill_file = PROJECT_ROOT / "skills" / "reverse-engineer" / "SKILL.md"
        assert skill_file.is_file(), f"Missing SKILL.md: {skill_file}"

    def test_skill_has_frontmatter(self) -> None:
        """SKILL.md has valid YAML frontmatter."""
        skill_file = PROJECT_ROOT / "skills" / "reverse-engineer" / "SKILL.md"
        content = skill_file.read_text()
        assert content.startswith("---"), "SKILL.md must start with YAML frontmatter"
        # Find closing ---
        second_dash = content.index("---", 3)
        assert second_dash > 3, "SKILL.md must have closing frontmatter delimiter"

    def test_skill_audience_is_both(self) -> None:
        """Skill audience is 'both' (works for OS dev AND project users)."""
        skill_file = PROJECT_ROOT / "skills" / "reverse-engineer" / "SKILL.md"
        content = skill_file.read_text()
        assert "audience: both" in content, "Skill audience must be 'both'"

    def test_skill_is_user_invocable(self) -> None:
        """Skill is user-invocable."""
        skill_file = PROJECT_ROOT / "skills" / "reverse-engineer" / "SKILL.md"
        content = skill_file.read_text()
        assert "user-invocable: true" in content

    def test_skill_references_config_schema_analysis(self) -> None:
        """SKILL.md references config schema analysis."""
        skill_file = PROJECT_ROOT / "skills" / "reverse-engineer" / "SKILL.md"
        content = skill_file.read_text().lower()
        assert "config schema" in content or "config_schema" in content

    def test_skill_references_env_var_analysis(self) -> None:
        """SKILL.md references environment variable analysis."""
        skill_file = PROJECT_ROOT / "skills" / "reverse-engineer" / "SKILL.md"
        content = skill_file.read_text().lower()
        assert "environment variable" in content or "env var" in content or "env_var" in content

    def test_skill_references_lib(self) -> None:
        """SKILL.md references the lib/reverse_engineer.py library."""
        skill_file = PROJECT_ROOT / "skills" / "reverse-engineer" / "SKILL.md"
        content = skill_file.read_text()
        assert "reverse_engineer" in content

    def test_skill_has_invocation_command(self) -> None:
        """SKILL.md documents /reverse-engineer invocation."""
        skill_file = PROJECT_ROOT / "skills" / "reverse-engineer" / "SKILL.md"
        content = skill_file.read_text()
        assert "/reverse-engineer" in content


class TestReverseEngineerLibExists:
    """Verify the lib module exists and has the expected API."""

    def test_lib_file_exists(self) -> None:
        """lib/reverse_engineer.py exists."""
        lib_file = PROJECT_ROOT / "lib" / "reverse_engineer.py"
        assert lib_file.is_file(), f"Missing lib file: {lib_file}"

    def test_lib_has_reverse_engineer_class(self) -> None:
        """lib has a ReverseEngineer class."""
        lib_file = PROJECT_ROOT / "lib" / "reverse_engineer.py"
        content = lib_file.read_text()
        assert "class ReverseEngineer" in content

    def test_lib_has_analyze_config_schema(self) -> None:
        """ReverseEngineer has analyze_config_schema method."""
        lib_file = PROJECT_ROOT / "lib" / "reverse_engineer.py"
        content = lib_file.read_text()
        assert "def analyze_config_schema" in content

    def test_lib_has_analyze_env_vars(self) -> None:
        """ReverseEngineer has analyze_env_vars method."""
        lib_file = PROJECT_ROOT / "lib" / "reverse_engineer.py"
        content = lib_file.read_text()
        assert "def analyze_env_vars" in content

    def test_lib_has_analyze_cli_commands(self) -> None:
        """ReverseEngineer has analyze_cli_commands method."""
        lib_file = PROJECT_ROOT / "lib" / "reverse_engineer.py"
        content = lib_file.read_text()
        assert "def analyze_cli_commands" in content

    def test_lib_has_analyze_api_routes(self) -> None:
        """ReverseEngineer has analyze_api_routes method."""
        lib_file = PROJECT_ROOT / "lib" / "reverse_engineer.py"
        content = lib_file.read_text()
        assert "def analyze_api_routes" in content

    def test_lib_has_analyze_docker_setup(self) -> None:
        """ReverseEngineer has analyze_docker_setup method."""
        lib_file = PROJECT_ROOT / "lib" / "reverse_engineer.py"
        content = lib_file.read_text()
        assert "def analyze_docker_setup" in content

    def test_lib_has_analyze_auth_flow(self) -> None:
        """ReverseEngineer has analyze_auth_flow method."""
        lib_file = PROJECT_ROOT / "lib" / "reverse_engineer.py"
        content = lib_file.read_text()
        assert "def analyze_auth_flow" in content

    def test_lib_has_format_integration_guide(self) -> None:
        """ReverseEngineer has format_integration_guide method."""
        lib_file = PROJECT_ROOT / "lib" / "reverse_engineer.py"
        content = lib_file.read_text()
        assert "def format_integration_guide" in content


class TestReverseEngineerInCatalog:
    """Verify the skill is listed in CATALOG.md."""

    def test_skill_in_catalog(self) -> None:
        """reverse-engineer skill appears in CATALOG.md."""
        catalog = PROJECT_ROOT / "skills" / "CATALOG.md"
        content = catalog.read_text()
        assert "reverse-engineer" in content, (
            "reverse-engineer skill must be listed in CATALOG.md"
        )

    def test_catalog_has_invoke_command(self) -> None:
        """CATALOG.md lists /reverse-engineer as the invoke command."""
        catalog = PROJECT_ROOT / "skills" / "CATALOG.md"
        content = catalog.read_text()
        assert "/reverse-engineer" in content
