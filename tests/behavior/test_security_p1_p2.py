"""Behavior tests for P1 and P2 security tool integrations.

Tests:
- Garak skill exists with audience: os-dev
- All documented tools appear in ecosystem-tools.md
- tero-testing package has valid cos-package.yaml
- mantis-security package has valid cos-package.yaml
- security-tools-landscape.md has implementation status column
- Install script for Garak exists
"""

import os
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ECOSYSTEM_TOOLS = PROJECT_ROOT / "packages" / "ecosystem-tools" / "rules" / "ecosystem-tools.md"
LANDSCAPE_FILE = PROJECT_ROOT / ".cognitive-os" / "plans" / "research" / "security-tools-landscape.md"
GARAK_SKILL = PROJECT_ROOT / "skills" / "vulnerability-scan" / "SKILL.md"
GARAK_INSTALL = PROJECT_ROOT / "scripts" / "install-garak.sh"
TERO_PACKAGE_DIR = PROJECT_ROOT / "packages" / "tero-testing"
MANTIS_PACKAGE_DIR = PROJECT_ROOT / "packages" / "mantis-security"


class TestGarakSkill:
    """Tests for the Garak vulnerability scan skill."""

    def test_skill_file_exists(self):
        assert GARAK_SKILL.exists(), "vulnerability-scan/SKILL.md must exist in skills/"

    def test_skill_has_frontmatter(self):
        content = GARAK_SKILL.read_text()
        assert content.startswith("---"), "SKILL.md must start with YAML frontmatter"
        # Extract frontmatter
        parts = content.split("---", 2)
        assert len(parts) >= 3, "SKILL.md must have closing frontmatter delimiter"

    def test_skill_audience_is_os_dev(self):
        content = GARAK_SKILL.read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        assert frontmatter.get("audience") == "os-dev", \
            "Garak skill audience must be 'os-dev'"

    def test_skill_has_name(self):
        content = GARAK_SKILL.read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        assert frontmatter.get("name") == "vulnerability-scan", \
            "Skill name must be 'vulnerability-scan'"

    def test_skill_has_version(self):
        content = GARAK_SKILL.read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        assert "version" in frontmatter, "Skill must have a version"

    def test_skill_references_garak(self):
        content = GARAK_SKILL.read_text()
        assert "garak" in content.lower(), "Skill must reference Garak"

    def test_skill_has_probe_categories(self):
        content = GARAK_SKILL.read_text()
        assert "injection" in content, "Skill must document injection probes"
        assert "leakage" in content, "Skill must document leakage probes"
        assert "hallucination" in content, "Skill must document hallucination probes"

    def test_skill_has_metrics_path(self):
        content = GARAK_SKILL.read_text()
        assert "garak-findings.jsonl" in content, \
            "Skill must reference metrics output path"


class TestGarakInstallScript:
    """Tests for the Garak install script."""

    def test_install_script_exists(self):
        assert GARAK_INSTALL.exists(), "scripts/install-garak.sh must exist"

    def test_install_script_has_shebang(self):
        content = GARAK_INSTALL.read_text()
        assert content.startswith("#!/usr/bin/env bash"), \
            "Install script must have bash shebang"

    def test_install_script_checks_python(self):
        content = GARAK_INSTALL.read_text()
        assert "python3" in content, \
            "Install script must check for Python 3"

    def test_install_script_installs_garak(self):
        content = GARAK_INSTALL.read_text()
        assert "pip install" in content and "garak" in content, \
            "Install script must install garak via pip"


class TestEcosystemToolsDocumentation:
    """Tests that all P1+P2 tools appear in ecosystem-tools.md."""

    def test_ecosystem_tools_file_exists(self):
        assert ECOSYSTEM_TOOLS.exists(), "ecosystem-tools.md must exist"

    def test_garak_documented(self):
        content = ECOSYSTEM_TOOLS.read_text()
        assert "garak" in content.lower(), "Garak must be documented in ecosystem-tools.md"

    def test_llamafirewall_documented(self):
        content = ECOSYSTEM_TOOLS.read_text()
        assert "LlamaFirewall" in content, \
            "LlamaFirewall must be documented in ecosystem-tools.md"

    def test_agentgateway_documented(self):
        content = ECOSYSTEM_TOOLS.read_text()
        assert "AgentGateway" in content, \
            "AgentGateway must be documented in ecosystem-tools.md"

    def test_onecli_documented(self):
        content = ECOSYSTEM_TOOLS.read_text()
        assert "OneCLI" in content, \
            "OneCLI must be documented in ecosystem-tools.md"

    def test_agentic_radar_documented(self):
        content = ECOSYSTEM_TOOLS.read_text()
        assert "Agentic Radar" in content, \
            "Agentic Radar must be documented in ecosystem-tools.md"

    def test_skill_scanner_documented(self):
        content = ECOSYSTEM_TOOLS.read_text()
        assert "skill-scanner" in content, \
            "skill-scanner must be documented in ecosystem-tools.md"

    def test_tero_documented(self):
        content = ECOSYSTEM_TOOLS.read_text()
        assert "tero" in content.lower(), \
            "tero must be documented in ecosystem-tools.md"

    def test_mantis_documented(self):
        content = ECOSYSTEM_TOOLS.read_text()
        assert "mantis" in content.lower(), \
            "mantis must be documented in ecosystem-tools.md"

    def test_tools_have_status_labels(self):
        """All P1+P2 tools must have a status label (ADOPT/EVALUATE/WATCH)."""
        content = ECOSYSTEM_TOOLS.read_text()
        for label in ["ADOPT", "EVALUATE", "WATCH"]:
            assert label in content, \
                f"ecosystem-tools.md must use '{label}' status labels"


class TestTeroTestingPackage:
    """Tests for the tero-testing COS package."""

    def test_package_dir_exists(self):
        assert TERO_PACKAGE_DIR.exists(), "packages/tero-testing/ must exist"

    def test_cos_package_yaml_exists(self):
        yaml_file = TERO_PACKAGE_DIR / "cos-package.yaml"
        assert yaml_file.exists(), "cos-package.yaml must exist"

    def test_cos_package_yaml_valid(self):
        yaml_file = TERO_PACKAGE_DIR / "cos-package.yaml"
        data = yaml.safe_load(yaml_file.read_text())
        assert data is not None, "cos-package.yaml must be valid YAML"
        assert "name" in data, "cos-package.yaml must have 'name'"
        assert "version" in data, "cos-package.yaml must have 'version'"
        assert "cos_version" in data, "cos-package.yaml must have 'cos_version'"

    def test_cos_package_name(self):
        yaml_file = TERO_PACKAGE_DIR / "cos-package.yaml"
        data = yaml.safe_load(yaml_file.read_text())
        assert data["name"] == "@luum/tero-testing", \
            "Package name must be '@luum/tero-testing'"

    def test_readme_exists(self):
        readme = TERO_PACKAGE_DIR / "README.md"
        assert readme.exists(), "README.md must exist in tero-testing package"

    def test_rule_file_exists(self):
        rule = TERO_PACKAGE_DIR / "rules" / "tero-integration.md"
        assert rule.exists(), "rules/tero-integration.md must exist"

    def test_rule_references_chaos(self):
        rule = TERO_PACKAGE_DIR / "rules" / "tero-integration.md"
        content = rule.read_text()
        assert "chaos" in content.lower(), \
            "tero integration rule must reference chaos engineering"


class TestMantisSecurityPackage:
    """Tests for the mantis-security COS package."""

    def test_package_dir_exists(self):
        assert MANTIS_PACKAGE_DIR.exists(), "packages/mantis-security/ must exist"

    def test_cos_package_yaml_exists(self):
        yaml_file = MANTIS_PACKAGE_DIR / "cos-package.yaml"
        assert yaml_file.exists(), "cos-package.yaml must exist"

    def test_cos_package_yaml_valid(self):
        yaml_file = MANTIS_PACKAGE_DIR / "cos-package.yaml"
        data = yaml.safe_load(yaml_file.read_text())
        assert data is not None, "cos-package.yaml must be valid YAML"
        assert "name" in data, "cos-package.yaml must have 'name'"
        assert "version" in data, "cos-package.yaml must have 'version'"
        assert "cos_version" in data, "cos-package.yaml must have 'cos_version'"

    def test_cos_package_name(self):
        yaml_file = MANTIS_PACKAGE_DIR / "cos-package.yaml"
        data = yaml.safe_load(yaml_file.read_text())
        assert data["name"] == "@luum/mantis-security", \
            "Package name must be '@luum/mantis-security'"

    def test_readme_exists(self):
        readme = MANTIS_PACKAGE_DIR / "README.md"
        assert readme.exists(), "README.md must exist in mantis-security package"

    def test_readme_references_owasp(self):
        readme = MANTIS_PACKAGE_DIR / "README.md"
        content = readme.read_text()
        assert "OWASP" in content, \
            "mantis README must reference OWASP coverage"


class TestSecurityToolsLandscape:
    """Tests for the security-tools-landscape.md research document."""

    def test_landscape_file_exists(self):
        assert LANDSCAPE_FILE.exists(), "security-tools-landscape.md must exist"

    def test_landscape_has_implementation_status(self):
        content = LANDSCAPE_FILE.read_text()
        assert "Implementation Status" in content, \
            "Landscape must have 'Implementation Status' column in Top 10 table"

    def test_landscape_tracks_done_status(self):
        content = LANDSCAPE_FILE.read_text()
        assert "**DONE**" in content, \
            "Landscape must track completed implementations with DONE status"

    def test_landscape_tracks_documented_status(self):
        content = LANDSCAPE_FILE.read_text()
        assert "**DOCUMENTED**" in content, \
            "Landscape must track documented tools with DOCUMENTED status"

    def test_landscape_references_tero_package(self):
        content = LANDSCAPE_FILE.read_text()
        assert "tero-testing" in content, \
            "Landscape must reference the tero-testing package"

    def test_landscape_references_mantis_package(self):
        content = LANDSCAPE_FILE.read_text()
        assert "mantis-security" in content, \
            "Landscape must reference the mantis-security package"
