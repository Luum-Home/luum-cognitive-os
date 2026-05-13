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


# =============================================================================
# TOOL 2: MCP-Scan (Invariant Labs)
# =============================================================================


class TestMcpScanHookFile:
    """Tests for the mcp-scan.sh hook file."""

    HOOK_PATH = PROJECT_ROOT / "hooks" / "mcp-scan.sh"


    def test_hook_has_shebang(self):
        content = self.HOOK_PATH.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Hook must have bash shebang"


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


class TestPromptfooConfig:
    """Tests for the Promptfoo configuration file."""

    CONFIG_PATH = PROJECT_ROOT / ".promptfoo" / "config.yaml"


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


# =============================================================================
# Install Scripts
# =============================================================================


class TestInstallScripts:
    """Tests for install scripts for all 3 tools."""


    def test_mcp_scan_install_script_has_shebang(self):
        path = PROJECT_ROOT / "scripts" / "install-mcp-scan.sh"
        content = path.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Install script must have bash shebang"


    def test_promptfoo_install_script_has_shebang(self):
        path = PROJECT_ROOT / "scripts" / "install-promptfoo.sh"
        content = path.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Install script must have bash shebang"


# =============================================================================
# Ecosystem Tools Documentation
# =============================================================================


class TestEcosystemToolsDoc:
    """Tests for ecosystem-tools.md references to all 3 tools."""

    ECOSYSTEM_PATH = PROJECT_ROOT / "packages" / "ecosystem-tools" / "rules" / "ecosystem-tools.md"


# =============================================================================
# Cognitive OS Configuration
# =============================================================================


class TestCognitiveOsConfig:
    """Tests for cognitive-os.yaml configuration sections."""

    CONFIG_PATH = PROJECT_ROOT / "cognitive-os.yaml"


    def test_config_mcp_scan_disabled_by_default(self):
        data = yaml.safe_load(self.CONFIG_PATH.read_text())
        assert data["security"]["mcp_scan"]["enabled"] is False, (
            "mcp_scan must be disabled by default"
        )


    def test_config_promptfoo_disabled_by_default(self):
        data = yaml.safe_load(self.CONFIG_PATH.read_text())
        assert "promptfoo" not in data["security"], (
            "promptfoo security config was intentionally removed; dead config must stay absent"
        )
