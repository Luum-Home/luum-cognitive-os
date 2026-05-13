"""Behavior tests for Aguara AI agent security scanner integration.

Tests:
- Hook file exists and follows conventions
- Hook has graceful degradation (checks command -v aguara)
- Hook follows PreToolUse pattern (exit 0 or 2)
- Hook skips non-Agent tool uses
- Hook skips in private mode
- Ecosystem tools doc references aguara
- Package cos-package.yaml is valid
- Config section exists in cognitive-os.yaml
- Install script exists
- Rule file documents key aspects
"""

import json
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = PROJECT_ROOT / "hooks" / "aguara-scan.sh"
PACKAGE_DIR = PROJECT_ROOT / "packages" / "aguara-security"
ECOSYSTEM_RULES = PROJECT_ROOT / "packages" / "ecosystem-tools" / "rules" / "ecosystem-tools.md"
RULE_FILE = PACKAGE_DIR / "rules" / "aguara-integration.md"
COS_PACKAGE = PACKAGE_DIR / "cos-package.yaml"
CONFIG_FILE = PROJECT_ROOT / "cognitive-os.yaml"
INSTALL_SCRIPT = PROJECT_ROOT / "scripts" / "install-aguara.sh"


class TestAguaraHookFile:
    """Tests for the aguara-scan.sh hook file."""

    def test_hook_file_exists(self):
        assert HOOK_PATH.exists(), "aguara-scan.sh must exist in hooks/"

    def test_hook_has_shebang(self):
        content = HOOK_PATH.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Hook must have bash shebang"

    def test_hook_sources_safe_jsonl(self):
        content = HOOK_PATH.read_text()
        assert "safe-jsonl.sh" in content, "Hook must source safe-jsonl.sh for JSONL writes"

    def test_hook_has_graceful_degradation(self):
        """Must check for aguara CLI and skip silently if not installed."""
        content = HOOK_PATH.read_text()
        assert "command -v aguara" in content, "Hook must check if aguara is installed"
        assert "exit 0" in content, "Hook must exit 0 when aguara is not found"

    def test_hook_checks_private_mode(self):
        content = HOOK_PATH.read_text()
        assert "claude-private-mode-active" in content, "Hook must check for private mode"

    def test_hook_filters_agent_tool_only(self):
        content = HOOK_PATH.read_text()
        assert "Agent" in content, "Hook must filter for Agent tool use"

    def test_hook_logs_to_jsonl(self):
        content = HOOK_PATH.read_text()
        assert "aguara-findings.jsonl" in content, "Hook must log findings to aguara-findings.jsonl"

    def test_hook_uses_adversarial_review_tiers(self):
        content = HOOK_PATH.read_text()
        assert "BLOCKER" in content, "Hook must use BLOCKER tier"
        assert "CONCERN" in content, "Hook must use CONCERN tier"
        assert "SUGGESTION" in content, "Hook must use SUGGESTION tier"

    def test_hook_blocks_on_critical(self):
        """CRITICAL findings must block agent launch (exit 2)."""
        content = HOOK_PATH.read_text()
        assert "exit 2" in content, "Hook must exit 2 on CRITICAL findings"


class TestAguaraHookExecution:
    """Tests for hook execution behavior."""

    def test_skips_when_aguara_not_installed(self, run_hook, cognitive_os_env):
        """Should gracefully skip when aguara binary is not available."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Test agent prompt"},
        })
        env = {
            **cognitive_os_env["env"],
            "PATH": "/usr/bin:/bin",  # Minimal PATH without aguara
        }
        result = run_hook("aguara-scan.sh", env=env, stdin=input_json)
        assert result.returncode == 0

    def test_skips_non_agent_tool(self, run_hook, cognitive_os_env):
        """Should not fire for non-Agent tools."""
        input_json = json.dumps({
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file"},
        })
        result = run_hook("aguara-scan.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        assert "AGUARA" not in result.stdout

    def test_skips_in_private_mode(self, run_hook, cognitive_os_env):
        """Should skip when private mode is active."""
        private_flag = Path("/tmp/claude-private-mode-active")
        try:
            private_flag.touch()
            input_json = json.dumps({
                "tool_name": "Agent",
                "tool_input": {"prompt": "Test agent prompt"},
            })
            result = run_hook("aguara-scan.sh", env=cognitive_os_env["env"], stdin=input_json)
            assert result.returncode == 0
            assert "AGUARA" not in result.stdout
        finally:
            private_flag.unlink(missing_ok=True)

    def test_skips_empty_prompt(self, run_hook, cognitive_os_env):
        """Should skip when agent prompt is empty."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {},
        })
        env = {
            **cognitive_os_env["env"],
            "PATH": "/usr/bin:/bin",
        }
        result = run_hook("aguara-scan.sh", env=env, stdin=input_json)
        assert result.returncode == 0


class TestAguaraPackage:
    """Tests for the cos package structure."""

    def test_package_dir_exists(self):
        assert PACKAGE_DIR.exists(), "packages/aguara-security/ must exist"

    def test_cos_package_yaml_exists(self):
        assert COS_PACKAGE.exists(), "cos-package.yaml must exist in package dir"

    def test_cos_package_yaml_valid(self):
        content = COS_PACKAGE.read_text()
        data = yaml.safe_load(content)
        assert data["name"] == "@luum/aguara-security"
        assert "version" in data
        assert "description" in data
        assert "cos_version" in data

    def test_cos_package_has_exports(self):
        data = yaml.safe_load(COS_PACKAGE.read_text())
        assert "exports" in data, "Package must declare exports"
        export_types = [e["type"] for e in data["exports"]]
        assert "rule" in export_types, "Package must export a rule"
        assert "hook" in export_types, "Package must export a hook"

    def test_rule_file_exists(self):
        assert RULE_FILE.exists(), "aguara-integration.md must exist in package rules/"

    def test_readme_exists(self):
        readme = PACKAGE_DIR / "README.md"
        assert readme.exists(), "README.md must exist in package dir"


class TestAguaraRuleFile:
    """Tests for the aguara-integration.md rule file."""

    def test_rule_documents_installation(self):
        content = RULE_FILE.read_text()
        assert "go install" in content, "Must document installation via go install"

    def test_rule_documents_graceful_degradation(self):
        content = RULE_FILE.read_text()
        assert "graceful" in content.lower() or "not installed" in content.lower(), (
            "Must document graceful degradation when aguara is not installed"
        )

    def test_rule_documents_severity_mapping(self):
        content = RULE_FILE.read_text()
        assert "BLOCKER" in content, "Must document BLOCKER tier mapping"
        assert "CONCERN" in content, "Must document CONCERN tier mapping"
        assert "SUGGESTION" in content, "Must document SUGGESTION tier mapping"

    def test_rule_documents_mcp_server(self):
        content = RULE_FILE.read_text()
        assert "mcp-aguara" in content, "Must document mcp-aguara MCP server"
        assert "scan_content" in content, "Must document scan_content tool"

    def test_rule_documents_jsonl_logging(self):
        content = RULE_FILE.read_text()
        assert "aguara-findings.jsonl" in content, "Must document JSONL log file"

    def test_rule_compares_with_parry(self):
        content = RULE_FILE.read_text()
        assert "parry" in content.lower(), "Must compare with parry for context"

    def test_rule_has_contextual_trigger(self):
        content = RULE_FILE.read_text()
        assert "Contextual Trigger" in content, "Must have contextual trigger section"


class TestEcosystemToolsIntegration:
    """Tests for ecosystem-tools.md update."""

    def test_ecosystem_tools_references_aguara(self):
        content = ECOSYSTEM_RULES.read_text()
        assert "aguara" in content.lower(), "ecosystem-tools.md must reference aguara"

    def test_ecosystem_tools_has_aguara_section(self):
        content = ECOSYSTEM_RULES.read_text()
        assert "### aguara" in content.lower() or "### Aguara" in content or "### aguara" in content, (
            "ecosystem-tools.md must have an aguara section header"
        )

    def test_ecosystem_tools_install_check_includes_aguara(self):
        content = ECOSYSTEM_RULES.read_text()
        assert "aguara" in content, "Installation status check must include aguara"


class TestCognitiveOsConfig:
    """Tests for cognitive-os.yaml aguara configuration."""

    def test_config_has_aguara_section(self):
        content = CONFIG_FILE.read_text()
        assert "aguara:" in content, "cognitive-os.yaml must have aguara section"

    def test_config_aguara_disabled_by_default(self):
        content = CONFIG_FILE.read_text()
        data = yaml.safe_load(content)
        assert data["security"]["aguara"]["enabled"] is False, (
            "aguara must be disabled by default in cognitive-os.yaml"
        )


class TestInstallScript:
    """Tests for the install script."""

    def test_install_script_exists(self):
        assert INSTALL_SCRIPT.exists(), "scripts/install-aguara.sh must exist"

    def test_install_script_has_shebang(self):
        content = INSTALL_SCRIPT.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Install script must have bash shebang"

    def test_install_script_installs_both_tools(self):
        content = INSTALL_SCRIPT.read_text()
        assert "garagon/aguara" in content, "Must install aguara"
        assert "garagon/mcp-aguara" in content, "Must install mcp-aguara"

    def test_install_script_checks_go(self):
        content = INSTALL_SCRIPT.read_text()
        assert "command -v go" in content or "go" in content, (
            "Must check for Go availability"
        )
