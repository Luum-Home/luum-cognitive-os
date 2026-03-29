"""Behavior tests for the e2b-sandbox COS package.

Validates that the package structure is correct, required files exist,
cos-package.yaml is valid, and the integration rule is well-formed.
"""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGE_DIR = PROJECT_ROOT / "packages" / "e2b-sandbox"


class TestPackageStructure:
    """e2b-sandbox package must have required files."""

    def test_package_directory_exists(self):
        """Package directory should exist."""
        assert PACKAGE_DIR.exists(), "packages/e2b-sandbox/ directory is missing"

    def test_cos_package_yaml_exists(self):
        """cos-package.yaml must exist."""
        assert (PACKAGE_DIR / "cos-package.yaml").exists(), "cos-package.yaml is missing"

    def test_readme_exists(self):
        """README.md must exist."""
        assert (PACKAGE_DIR / "README.md").exists(), "README.md is missing"

    def test_readme_not_empty(self):
        """README should contain substantial content."""
        readme = (PACKAGE_DIR / "README.md").read_text()
        assert len(readme) > 200, "README.md is too short to be useful"

    def test_rules_directory_exists(self):
        """Rules directory should exist."""
        assert (PACKAGE_DIR / "rules").is_dir(), "rules/ directory is missing"

    def test_integration_rule_exists(self):
        """e2b-integration.md rule must exist."""
        rule_path = PACKAGE_DIR / "rules" / "e2b-integration.md"
        assert rule_path.exists(), "rules/e2b-integration.md is missing"


class TestCosPackageYaml:
    """cos-package.yaml must be valid and contain required fields."""

    @pytest.fixture
    def package_config(self):
        """Load and parse cos-package.yaml."""
        content = (PACKAGE_DIR / "cos-package.yaml").read_text()
        return yaml.safe_load(content)

    def test_yaml_is_valid(self, package_config):
        """YAML should parse without errors."""
        assert package_config is not None, "cos-package.yaml failed to parse"

    def test_has_name(self, package_config):
        """Package must have a name field."""
        assert "name" in package_config, "Missing 'name' field"
        assert package_config["name"] == "@luum/e2b-sandbox"

    def test_has_version(self, package_config):
        """Package must have a version field."""
        assert "version" in package_config, "Missing 'version' field"

    def test_has_description(self, package_config):
        """Package must have a description field."""
        assert "description" in package_config, "Missing 'description' field"
        assert len(package_config["description"]) > 20, "Description is too short"

    def test_has_license(self, package_config):
        """Package must have a license field."""
        assert "license" in package_config, "Missing 'license' field"
        assert package_config["license"] == "Apache-2.0"

    def test_has_cos_version(self, package_config):
        """Package must declare minimum COS version."""
        assert "cos_version" in package_config, "Missing 'cos_version' field"

    def test_has_provides(self, package_config):
        """Package must declare what it provides."""
        assert "provides" in package_config, "Missing 'provides' field"
        assert "rule" in package_config["provides"]

    def test_has_exports(self, package_config):
        """Package must declare exports."""
        assert "exports" in package_config, "Missing 'exports' field"
        assert len(package_config["exports"]) > 0, "No exports declared"

    def test_exports_reference_existing_files(self, package_config):
        """All exported files must exist."""
        for export in package_config.get("exports", []):
            source = export.get("source", "")
            file_path = PACKAGE_DIR / source
            assert file_path.exists(), f"Exported file does not exist: {source}"

    def test_has_keywords(self, package_config):
        """Package should have keywords for discoverability."""
        assert "keywords" in package_config, "Missing 'keywords' field"
        keywords = package_config["keywords"]
        assert "e2b" in keywords, "'e2b' should be in keywords"
        assert "sandbox" in keywords, "'sandbox' should be in keywords"


class TestIntegrationRule:
    """e2b-integration.md must be well-formed and contain key sections."""

    @pytest.fixture
    def rule_content(self):
        """Read the integration rule content."""
        return (PACKAGE_DIR / "rules" / "e2b-integration.md").read_text()

    def test_rule_not_empty(self, rule_content):
        """Rule should contain substantial content."""
        assert len(rule_content) > 500, "Integration rule is too short"

    def test_has_overview_section(self, rule_content):
        """Rule should have an overview section."""
        assert "## Overview" in rule_content, "Missing '## Overview' section"

    def test_has_installation_section(self, rule_content):
        """Rule should document installation."""
        assert "## Installation" in rule_content or "## Install" in rule_content, (
            "Missing installation section"
        )

    def test_has_mcp_configuration(self, rule_content):
        """Rule should document MCP server configuration."""
        assert "mcpServers" in rule_content, "Missing MCP server configuration"
        assert "@e2b/mcp-server" in rule_content, "Missing @e2b/mcp-server reference"

    def test_has_when_to_use_section(self, rule_content):
        """Rule should document when to use sandboxes."""
        assert "When to Use" in rule_content, "Missing 'When to Use' guidance"

    def test_has_graceful_degradation(self, rule_content):
        """Rule should document graceful degradation."""
        assert "Graceful Degradation" in rule_content, (
            "Missing graceful degradation section"
        )

    def test_has_contextual_trigger(self, rule_content):
        """Rule should have a contextual trigger section."""
        assert "## Contextual Trigger" in rule_content, (
            "Missing contextual trigger section"
        )

    def test_references_e2b_api_key(self, rule_content):
        """Rule should reference the E2B_API_KEY environment variable."""
        assert "E2B_API_KEY" in rule_content, "Missing E2B_API_KEY reference"

    def test_references_security_model(self, rule_content):
        """Rule should document security considerations."""
        assert "Security" in rule_content or "security" in rule_content, (
            "Missing security documentation"
        )


class TestReadmeContent:
    """README.md should document setup and usage."""

    @pytest.fixture
    def readme_content(self):
        """Read the README content."""
        return (PACKAGE_DIR / "README.md").read_text()

    def test_has_setup_instructions(self, readme_content):
        """README should have setup instructions."""
        assert "Setup" in readme_content or "Install" in readme_content, (
            "Missing setup instructions"
        )

    def test_has_mcp_server_config(self, readme_content):
        """README should show MCP server configuration."""
        assert "mcpServers" in readme_content, "Missing MCP server config example"

    def test_has_api_key_instructions(self, readme_content):
        """README should document API key setup."""
        assert "E2B_API_KEY" in readme_content, "Missing API key instructions"

    def test_has_available_tools(self, readme_content):
        """README should list available tools."""
        assert "e2b_execute_code" in readme_content or "Available Tools" in readme_content, (
            "Missing available tools documentation"
        )

    def test_references_e2b_docs(self, readme_content):
        """README should link to official E2B documentation."""
        assert "e2b.dev" in readme_content, "Missing link to E2B documentation"
