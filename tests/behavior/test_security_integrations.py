"""Behavior tests for P0 security tool integrations.

Tests 3 integrations:
1. Semgrep AI Best Practices ruleset (config change)
2. MCP-Scan (Invariant Labs) — MCP server configuration scanner
3. Promptfoo — LLM red team testing

Each integration follows the ecosystem-tools pattern:
- Graceful degradation (optional dependency)
- JSONL metrics logging
- Documentation in ecosystem-tools.md
- Configuration in cognitive-os.yaml
"""

import json
import os
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# =============================================================================
# TOOL 1: Semgrep AI Best Practices Ruleset
# =============================================================================


class TestSemgrepAiBestPractices:
    """Tests for the ai-best-practices ruleset addition to Semgrep."""

    HOOK_PATH = PROJECT_ROOT / "hooks" / "semgrep-scan.sh"
    RULE_FILE = PROJECT_ROOT / "rules" / "security-scanning.md"

    def test_hook_includes_ai_best_practices_config(self):
        """semgrep-scan.sh must include --config p/ai-best-practices."""
        content = self.HOOK_PATH.read_text()
        assert "p/ai-best-practices" in content, (
            "Hook must include --config p/ai-best-practices alongside auto"
        )

    def test_hook_still_includes_auto_config(self):
        """semgrep-scan.sh must still include --config auto."""
        content = self.HOOK_PATH.read_text()
        assert "--config auto" in content, (
            "Hook must retain --config auto for community rules"
        )

    def test_hook_has_both_configs_in_single_command(self):
        """Both configs must appear in the same semgrep scan command."""
        content = self.HOOK_PATH.read_text()
        # Find the semgrep scan line
        for line in content.splitlines():
            if "semgrep scan" in line and "--json" in line:
                assert "--config auto" in line, "auto config must be in scan command"
                assert "--config p/ai-best-practices" in line, (
                    "ai-best-practices config must be in scan command"
                )
                break
        else:
            pytest.fail("Could not find semgrep scan command line in hook")

    def test_rule_file_documents_ai_best_practices(self):
        """security-scanning.md must document the ai-best-practices ruleset."""
        content = self.RULE_FILE.read_text()
        assert "ai-best-practices" in content, (
            "Rule file must document the ai-best-practices ruleset"
        )

    def test_rule_file_documents_ruleset_categories(self):
        """security-scanning.md must describe what the ruleset detects."""
        content = self.RULE_FILE.read_text()
        # Should mention at least some categories
        assert "hardcoded" in content.lower() or "api key" in content.lower(), (
            "Rule file must mention hardcoded keys detection"
        )
        assert "prompt injection" in content.lower() or "injection" in content.lower(), (
            "Rule file must mention injection detection"
        )


# =============================================================================
# TOOL 2: MCP-Scan (Invariant Labs)
# =============================================================================


class TestMcpScanHookFile:
    """Tests for the mcp-scan.sh hook file."""

    HOOK_PATH = PROJECT_ROOT / "hooks" / "mcp-scan.sh"

    def test_hook_file_exists(self):
        assert self.HOOK_PATH.exists(), "mcp-scan.sh must exist in hooks/"

    def test_hook_has_shebang(self):
        content = self.HOOK_PATH.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Hook must have bash shebang"

    def test_hook_sources_safe_jsonl(self):
        content = self.HOOK_PATH.read_text()
        assert "safe-jsonl.sh" in content, "Hook must source safe-jsonl.sh for JSONL writes"

    def test_hook_has_graceful_degradation(self):
        """Must check for mcp-scan CLI and skip silently if not installed."""
        content = self.HOOK_PATH.read_text()
        assert "mcp-scan" in content, "Hook must reference mcp-scan command"
        assert "exit 0" in content, "Hook must exit 0 when mcp-scan is not found"

    def test_hook_checks_private_mode(self):
        content = self.HOOK_PATH.read_text()
        assert "claude-private-mode-active" in content, "Hook must check for private mode"

    def test_hook_is_session_start_pattern(self):
        """MCP-scan should follow SessionStart hook pattern (no tool_name filter)."""
        content = self.HOOK_PATH.read_text()
        # SessionStart hooks scan files, not tool input
        assert "settings.json" in content, "Hook must scan settings.json files"

    def test_hook_logs_to_jsonl(self):
        content = self.HOOK_PATH.read_text()
        assert "mcp-scan-findings.jsonl" in content, (
            "Hook must log findings to mcp-scan-findings.jsonl"
        )

    def test_hook_uses_adversarial_review_tiers(self):
        content = self.HOOK_PATH.read_text()
        assert "BLOCKER" in content, "Hook must use BLOCKER tier"
        assert "CONCERN" in content, "Hook must use CONCERN tier"
        assert "SUGGESTION" in content, "Hook must use SUGGESTION tier"

    def test_hook_is_advisory_only(self):
        """MCP-scan must never block session start (always exit 0)."""
        content = self.HOOK_PATH.read_text()
        # Should NOT have exit 2 (blocking exit)
        lines = content.splitlines()
        # The last exit should be exit 0
        exit_lines = [l.strip() for l in lines if l.strip().startswith("exit")]
        assert exit_lines[-1] == "exit 0", (
            "Hook must end with exit 0 (advisory only, never blocks)"
        )

    def test_hook_scans_mcp_server_configs(self):
        """Must scan for mcpServers in settings files."""
        content = self.HOOK_PATH.read_text()
        assert "mcpServers" in content, "Hook must check for mcpServers section"


class TestMcpScanHookExecution:
    """Tests for MCP-scan hook execution behavior."""

    def test_skips_when_mcp_scan_not_installed(self, run_hook, cognitive_os_env):
        """Should gracefully skip when mcp-scan is not available."""
        result = run_hook(
            "mcp-scan.sh",
            env={
                **cognitive_os_env["env"],
                "PATH": "/usr/bin:/bin",  # Minimal PATH without mcp-scan
            },
        )
        assert result.returncode == 0

    def test_skips_in_private_mode(self, run_hook, cognitive_os_env):
        """Should skip when private mode is active."""
        private_flag = Path("/tmp/claude-private-mode-active")
        try:
            private_flag.touch()
            result = run_hook("mcp-scan.sh", env=cognitive_os_env["env"])
            assert result.returncode == 0
            assert "MCP-SCAN" not in result.stdout
        finally:
            private_flag.unlink(missing_ok=True)


# =============================================================================
# TOOL 3: Promptfoo Red Team Testing
# =============================================================================


class TestRedTeamSkill:
    """Tests for the red-team skill definition."""

    SKILL_PATH = PROJECT_ROOT / "skills" / "red-team" / "SKILL.md"

    def test_skill_file_exists(self):
        assert self.SKILL_PATH.exists(), "skills/red-team/SKILL.md must exist"

    def test_skill_has_frontmatter(self):
        content = self.SKILL_PATH.read_text()
        # SKILL.md starts with # title, then ---, then frontmatter, then ---
        assert "---" in content, "Must have YAML frontmatter delimiters"

    def test_skill_has_audience_os_dev(self):
        content = self.SKILL_PATH.read_text()
        assert "audience: os-dev" in content, "Skill audience must be os-dev"

    def test_skill_references_promptfoo(self):
        content = self.SKILL_PATH.read_text()
        assert "promptfoo" in content.lower(), "Skill must reference promptfoo"

    def test_skill_has_trigger(self):
        content = self.SKILL_PATH.read_text()
        assert "/red-team" in content, "Skill must have /red-team trigger"

    def test_skill_documents_metrics_output(self):
        content = self.SKILL_PATH.read_text()
        assert "red-team-results" in content, "Skill must document results output"

    def test_skill_uses_adversarial_review_format(self):
        content = self.SKILL_PATH.read_text()
        assert "BLOCKER" in content, "Skill must use BLOCKER tier in report format"

    def test_skill_documents_engram_save(self):
        content = self.SKILL_PATH.read_text()
        assert "mem_save" in content, "Skill must document saving findings to Engram"


class TestPromptfooConfig:
    """Tests for the Promptfoo configuration file."""

    CONFIG_PATH = PROJECT_ROOT / ".promptfoo" / "config.yaml"

    def test_config_file_exists(self):
        assert self.CONFIG_PATH.exists(), ".promptfoo/config.yaml must exist"

    def test_config_is_valid_yaml(self):
        content = self.CONFIG_PATH.read_text()
        data = yaml.safe_load(content)
        assert data is not None, "Config must be valid YAML"

    def test_config_has_tests(self):
        data = yaml.safe_load(self.CONFIG_PATH.read_text())
        assert "tests" in data, "Config must define test cases"
        assert len(data["tests"]) > 0, "Config must have at least one test case"

    def test_config_has_prompt_injection_tests(self):
        data = yaml.safe_load(self.CONFIG_PATH.read_text())
        descriptions = [t.get("description", "").lower() for t in data["tests"]]
        injection_tests = [d for d in descriptions if "injection" in d]
        assert len(injection_tests) > 0, "Config must have prompt injection test cases"

    def test_config_has_jailbreak_tests(self):
        data = yaml.safe_load(self.CONFIG_PATH.read_text())
        descriptions = [t.get("description", "").lower() for t in data["tests"]]
        jailbreak_tests = [d for d in descriptions if "jailbreak" in d or "base64" in d]
        assert len(jailbreak_tests) > 0, "Config must have jailbreak test cases"

    def test_config_has_data_exfiltration_tests(self):
        data = yaml.safe_load(self.CONFIG_PATH.read_text())
        descriptions = [t.get("description", "").lower() for t in data["tests"]]
        exfil_tests = [d for d in descriptions if "exfil" in d or "api key" in d or "extract" in d or ".env" in d]
        assert len(exfil_tests) > 0, "Config must have data exfiltration test cases"

    def test_config_has_assertions(self):
        """Every test case must have at least one assertion."""
        data = yaml.safe_load(self.CONFIG_PATH.read_text())
        for test in data["tests"]:
            assert "assert" in test, (
                f"Test '{test.get('description', 'unknown')}' must have assertions"
            )


# =============================================================================
# Install Scripts
# =============================================================================


class TestInstallScripts:
    """Tests for install scripts for all 3 tools."""

    def test_mcp_scan_install_script_exists(self):
        path = PROJECT_ROOT / "scripts" / "install-mcp-scan.sh"
        assert path.exists(), "scripts/install-mcp-scan.sh must exist"

    def test_mcp_scan_install_script_has_shebang(self):
        path = PROJECT_ROOT / "scripts" / "install-mcp-scan.sh"
        content = path.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Install script must have bash shebang"

    def test_mcp_scan_install_references_pip(self):
        path = PROJECT_ROOT / "scripts" / "install-mcp-scan.sh"
        content = path.read_text()
        assert "pip" in content, "Must reference pip installation method"

    def test_promptfoo_install_script_exists(self):
        path = PROJECT_ROOT / "scripts" / "install-promptfoo.sh"
        assert path.exists(), "scripts/install-promptfoo.sh must exist"

    def test_promptfoo_install_script_has_shebang(self):
        path = PROJECT_ROOT / "scripts" / "install-promptfoo.sh"
        content = path.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Install script must have bash shebang"

    def test_promptfoo_install_references_npm(self):
        path = PROJECT_ROOT / "scripts" / "install-promptfoo.sh"
        content = path.read_text()
        assert "npm" in content or "npx" in content, (
            "Must reference npm or npx installation method"
        )

    def test_promptfoo_install_checks_node(self):
        path = PROJECT_ROOT / "scripts" / "install-promptfoo.sh"
        content = path.read_text()
        assert "node" in content, "Must check for Node.js availability"


# =============================================================================
# Ecosystem Tools Documentation
# =============================================================================


class TestEcosystemToolsDoc:
    """Tests for ecosystem-tools.md references to all 3 tools."""

    ECOSYSTEM_PATH = PROJECT_ROOT / "packages" / "ecosystem-tools" / "rules" / "ecosystem-tools.md"

    def test_references_mcp_scan(self):
        content = self.ECOSYSTEM_PATH.read_text()
        assert "mcp-scan" in content, "Must reference mcp-scan"

    def test_references_promptfoo(self):
        content = self.ECOSYSTEM_PATH.read_text()
        assert "promptfoo" in content, "Must reference promptfoo"

    def test_mcp_scan_has_section(self):
        content = self.ECOSYSTEM_PATH.read_text()
        assert "### mcp-scan" in content, "Must have mcp-scan section header"

    def test_promptfoo_has_section(self):
        content = self.ECOSYSTEM_PATH.read_text()
        assert "### promptfoo" in content, "Must have promptfoo section header"

    def test_install_check_includes_mcp_scan(self):
        content = self.ECOSYSTEM_PATH.read_text()
        assert "mcp-scan" in content, "Installation status check must include mcp-scan"

    def test_install_check_includes_promptfoo(self):
        content = self.ECOSYSTEM_PATH.read_text()
        assert "promptfoo" in content, "Installation status check must include promptfoo"


# =============================================================================
# Cognitive OS Configuration
# =============================================================================


class TestCognitiveOsConfig:
    """Tests for cognitive-os.yaml configuration sections."""

    CONFIG_PATH = PROJECT_ROOT / "cognitive-os.yaml"

    def test_config_has_mcp_scan_section(self):
        content = self.CONFIG_PATH.read_text()
        assert "mcp_scan:" in content, "Must have mcp_scan section"

    def test_config_mcp_scan_disabled_by_default(self):
        data = yaml.safe_load(self.CONFIG_PATH.read_text())
        assert data["security"]["mcp_scan"]["enabled"] is False, (
            "mcp_scan must be disabled by default"
        )

    def test_config_has_promptfoo_section(self):
        content = self.CONFIG_PATH.read_text()
        assert "promptfoo:" in content, "Must have promptfoo section"

    def test_config_promptfoo_disabled_by_default(self):
        data = yaml.safe_load(self.CONFIG_PATH.read_text())
        assert data["security"]["promptfoo"]["enabled"] is False, (
            "promptfoo must be disabled by default"
        )

    def test_config_promptfoo_has_config_path(self):
        data = yaml.safe_load(self.CONFIG_PATH.read_text())
        assert "config" in data["security"]["promptfoo"], (
            "promptfoo must have config path"
        )
