"""Unit tests for NeMo Guardrails integration.

Validates:
- Config file structure and validity
- Colang 2.0 syntax basic checks
- Rule mapping coverage (Cognitive OS rules -> Colang rails)
"""

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
NEMO_CONFIG_DIR = PROJECT_ROOT / "infra" / "nemo-guardrails" / "config"
NEMO_CONFIG_FILE = NEMO_CONFIG_DIR / "config.yml"
NEMO_RAILS_FILE = NEMO_CONFIG_DIR / "rails.co"
NEMO_DOCKERFILE = PROJECT_ROOT / "infra" / "nemo-guardrails" / "Dockerfile"


# ---------------------------------------------------------------------------
# Config file validation
# ---------------------------------------------------------------------------


class TestNemoConfigFile:
    """Tests for infra/nemo-guardrails/config/config.yml."""

    def test_config_file_exists(self):
        assert NEMO_CONFIG_FILE.exists(), "NeMo config file must exist"

    def test_config_is_valid_yaml(self):
        content = NEMO_CONFIG_FILE.read_text()
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict), "Config must be a YAML dict"

    def test_config_has_rails_section(self):
        parsed = yaml.safe_load(NEMO_CONFIG_FILE.read_text())
        assert "rails" in parsed, "Config must have a 'rails' section"

    def test_config_has_input_rails(self):
        parsed = yaml.safe_load(NEMO_CONFIG_FILE.read_text())
        rails = parsed.get("rails", {})
        assert "input" in rails, "Config must define input rails"
        input_flows = rails["input"].get("flows", [])
        assert len(input_flows) >= 1, "At least one input rail flow expected"

    def test_config_has_output_rails(self):
        parsed = yaml.safe_load(NEMO_CONFIG_FILE.read_text())
        rails = parsed.get("rails", {})
        assert "output" in rails, "Config must define output rails"
        output_flows = rails["output"].get("flows", [])
        assert len(output_flows) >= 1, "At least one output rail flow expected"

    def test_config_specifies_colang_version(self):
        parsed = yaml.safe_load(NEMO_CONFIG_FILE.read_text())
        assert "colang_version" in parsed, "Config must specify colang_version"
        assert parsed["colang_version"] == "2.0", "Must use Colang 2.0"

    def test_config_has_models_section(self):
        parsed = yaml.safe_load(NEMO_CONFIG_FILE.read_text())
        assert "models" in parsed, "Config must have a 'models' section"


# ---------------------------------------------------------------------------
# Colang syntax basic checks
# ---------------------------------------------------------------------------


class TestColangSyntax:
    """Basic syntax validation for rails.co Colang 2.0 file."""

    def test_rails_file_exists(self):
        assert NEMO_RAILS_FILE.exists(), "Colang rails file must exist"

    def test_rails_file_not_empty(self):
        content = NEMO_RAILS_FILE.read_text()
        assert len(content.strip()) > 100, "Rails file should have substantial content"

    def test_has_define_flow_statements(self):
        content = NEMO_RAILS_FILE.read_text()
        flows = re.findall(r"^define flow .+", content, re.MULTILINE)
        assert len(flows) >= 3, f"Expected at least 3 flow definitions, found {len(flows)}"

    def test_has_define_bot_statements(self):
        content = NEMO_RAILS_FILE.read_text()
        bots = re.findall(r"^define bot .+", content, re.MULTILINE)
        assert len(bots) >= 2, f"Expected at least 2 bot definitions, found {len(bots)}"

    def test_no_colang_v1_syntax(self):
        """Ensure no Colang v1 syntax (define subflow, define user, etc.)."""
        content = NEMO_RAILS_FILE.read_text()
        assert "define subflow" not in content, "Colang v1 'define subflow' found"
        assert "define user" not in content.replace(
            "define user said", ""
        ).replace("user said", ""), "Should use 'user said something' not 'define user'"

    def test_indentation_uses_spaces(self):
        """Colang 2.0 requires space indentation, not tabs."""
        content = NEMO_RAILS_FILE.read_text()
        for i, line in enumerate(content.split("\n"), 1):
            assert "\t" not in line, f"Tab found on line {i}: {line[:50]}"

    def test_flow_names_are_descriptive(self):
        content = NEMO_RAILS_FILE.read_text()
        flows = re.findall(r"^define flow (.+)", content, re.MULTILINE)
        for flow in flows:
            assert len(flow.strip()) >= 10, f"Flow name too short: '{flow}'"


# ---------------------------------------------------------------------------
# Rule mapping coverage
# ---------------------------------------------------------------------------


class TestRuleMappingCoverage:
    """Verify that key Cognitive OS rules are mapped to Colang rails."""

    @pytest.fixture(autouse=True)
    def load_rails(self):
        self.rails_content = NEMO_RAILS_FILE.read_text().lower()

    def test_clarification_gate_mapped(self):
        """clarification-gate -> input rail for blocking vague prompts."""
        assert "block vague prompts" in self.rails_content or "vague" in self.rails_content, (
            "clarification-gate rule not mapped to Colang"
        )

    def test_assumption_tracker_mapped(self):
        """assumption-tracker -> output rail for flagging assumptions."""
        assert "assumption" in self.rails_content, (
            "assumption-tracker rule not mapped to Colang"
        )

    def test_confidence_gate_mapped(self):
        """confidence-gate -> output rail for low confidence."""
        assert "confidence" in self.rails_content, (
            "confidence-gate rule not mapped to Colang"
        )

    def test_credential_management_mapped(self):
        """credential-management -> output rail for credential leaks."""
        assert "credential" in self.rails_content, (
            "credential-management rule not mapped to Colang"
        )

    def test_prompt_injection_mapped(self):
        """Security best practice -> input rail for prompt injection."""
        assert "prompt injection" in self.rails_content or "ignore previous" in self.rails_content, (
            "Prompt injection defense not mapped to Colang"
        )

    def test_api_key_patterns_present(self):
        """Output rail should detect common API key patterns."""
        patterns_found = sum(
            1
            for pattern in ["sk-", "api", "bearer", "ghp_", "akia"]
            if pattern in self.rails_content
        )
        assert patterns_found >= 3, (
            f"Expected at least 3 API key patterns, found {patterns_found}"
        )

    def test_input_and_output_rails_present(self):
        """Must have both input and output rail flows."""
        assert "input" in self.rails_content, "Input rails missing"
        # Check for user-triggered flows (input) and bot-triggered flows (output)
        assert "user said" in self.rails_content, "No user-triggered (input) flows"
        assert "bot said" in self.rails_content, "No bot-triggered (output) flows"


# ---------------------------------------------------------------------------
# Dockerfile validation
# ---------------------------------------------------------------------------


class TestNemoDockerfile:
    """Validate the NeMo Guardrails Dockerfile."""

    def test_dockerfile_exists(self):
        assert NEMO_DOCKERFILE.exists(), "Dockerfile must exist"

    def test_dockerfile_installs_nemoguardrails(self):
        content = NEMO_DOCKERFILE.read_text()
        assert "nemoguardrails" in content, "Dockerfile must install nemoguardrails"

    def test_dockerfile_copies_config(self):
        content = NEMO_DOCKERFILE.read_text()
        assert "COPY config/" in content or "COPY ./config" in content, (
            "Dockerfile must copy config directory"
        )

    def test_dockerfile_exposes_port(self):
        content = NEMO_DOCKERFILE.read_text()
        assert "EXPOSE 8088" in content, "Dockerfile must expose port 8088"

    def test_dockerfile_has_cmd(self):
        content = NEMO_DOCKERFILE.read_text()
        assert "CMD" in content, "Dockerfile must have a CMD instruction"


# ---------------------------------------------------------------------------
# Skill file validation
# ---------------------------------------------------------------------------


class TestNemoSkillFile:
    """Validate the nemo-guardrails skill definition."""

    SKILL_FILE = PROJECT_ROOT / "skills" / "nemo-guardrails" / "SKILL.md"

    def test_skill_file_exists(self):
        assert self.SKILL_FILE.exists(), "SKILL.md must exist"

    def test_skill_has_frontmatter(self):
        content = self.SKILL_FILE.read_text()
        assert content.startswith("---"), "SKILL.md must start with YAML frontmatter"
        # Find second --- delimiter
        second_delim = content.index("---", 3)
        assert second_delim > 0, "SKILL.md must have closing frontmatter delimiter"

    def test_skill_has_invocation(self):
        content = self.SKILL_FILE.read_text()
        assert "/nemo-setup" in content, "SKILL.md must document /nemo-setup invocation"

    def test_skill_references_rule_mapping(self):
        content = self.SKILL_FILE.read_text()
        for rule in ["clarification-gate", "assumption-tracker", "confidence-gate", "credential"]:
            assert rule in content, f"SKILL.md must reference {rule} rule"
