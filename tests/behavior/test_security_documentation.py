"""Behavior tests for security documentation completeness and accuracy.

Verifies that docs/security-stack.md is the comprehensive master security
document and that it stays in sync with the actual hooks, rules, and tools.
"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def security_stack_path() -> Path:
    return PROJECT_ROOT / "docs" / "security-stack.md"


@pytest.fixture
def safety_mesh_path() -> Path:
    return PROJECT_ROOT / "docs" / "safety-mesh.md"


@pytest.fixture
def security_stack_content(security_stack_path: Path) -> str:
    assert security_stack_path.exists(), "docs/security-stack.md must exist"
    return security_stack_path.read_text()


@pytest.fixture
def safety_mesh_content(safety_mesh_path: Path) -> str:
    assert safety_mesh_path.exists(), "docs/safety-mesh.md must exist"
    return safety_mesh_path.read_text()


class TestSecurityStackExists:
    """Basic structural tests for security-stack.md."""

    def test_file_exists(self, security_stack_path: Path):
        assert security_stack_path.exists(), "docs/security-stack.md must exist"

    def test_minimum_length(self, security_stack_content: str):
        lines = security_stack_content.strip().splitlines()
        assert len(lines) > 200, (
            f"security-stack.md has {len(lines)} lines, expected >200"
        )

    def test_has_title(self, security_stack_content: str):
        assert "# Cognitive OS Security Stack" in security_stack_content


class TestSecurityStackStructure:
    """Tests for required sections in security-stack.md."""

    def test_has_posture_summary(self, security_stack_content: str):
        assert "Security Posture Summary" in security_stack_content

    def test_has_gap_analysis(self, security_stack_content: str):
        assert "Gap Analysis" in security_stack_content

    def test_has_how_to_add_section(self, security_stack_content: str):
        assert "How to Add a New Security Tool" in security_stack_content

    def test_has_summary_table_with_counts(self, security_stack_content: str):
        assert "Active defense layers" in security_stack_content
        assert "Optional tools" in security_stack_content
        assert "Planned integrations" in security_stack_content

    def test_has_attack_vectors_section(self, security_stack_content: str):
        assert "Attack Vectors and Defenses" in security_stack_content

    def test_has_graceful_degradation_section(self, security_stack_content: str):
        assert "Graceful Degradation" in security_stack_content

    def test_has_references_section(self, security_stack_content: str):
        assert "## References" in security_stack_content

    def test_has_installation_guide(self, security_stack_content: str):
        assert "Installation Guide" in security_stack_content


class TestSecurityStackLayers:
    """Tests that all 8 layers are documented."""

    EXPECTED_LAYERS = [
        "Layer 1",
        "Layer 2",
        "Layer 3",
        "Layer 4",
        "Layer 5",
        "Layer 6",
        "Layer 7",
        "Layer 8",
    ]

    @pytest.mark.parametrize("layer", EXPECTED_LAYERS)
    def test_layer_exists(self, security_stack_content: str, layer: str):
        assert layer in security_stack_content, f"Missing {layer} in security-stack.md"

    def test_layer_topics(self, security_stack_content: str):
        assert "Input Validation" in security_stack_content
        assert "Permission" in security_stack_content
        assert "Code Security" in security_stack_content
        assert "MCP Security" in security_stack_content
        assert "Supply Chain" in security_stack_content
        assert "Output Validation" in security_stack_content
        assert "Runtime Protection" in security_stack_content
        assert "Red Team" in security_stack_content or "Testing" in security_stack_content


class TestActiveHooksReferenced:
    """Verifies that all active security hooks are referenced in the document."""

    ACTIVE_HOOKS = [
        "clarification-gate",
        "blast-radius",
        "rate-limiter",
        "scope-proportionality",
        "claim-validator",
        "assumption-tracker",
        "trust-score-validator",
        "confidence-gate",
        "clarification-interceptor",
        "auto-rollback",
        "content-policy",
        "secret-detector",
        "scope-creep-detector",
        "dry-run-preview",
        "rate-limit-protection",
    ]

    @pytest.mark.parametrize("hook", ACTIVE_HOOKS)
    def test_hook_referenced(self, security_stack_content: str, hook: str):
        assert hook in security_stack_content, (
            f"Active hook '{hook}' not referenced in security-stack.md"
        )


class TestOptionalToolsReferenced:
    """Verifies that optional and planned tools are referenced."""

    OPTIONAL_TOOLS = [
        "Aguara",
        "Parry",
        "Semgrep",
        "Trail of Bits",
        "NeMo Guardrails",
        "Garak",
    ]

    PLANNED_TOOLS = [
        "MCP-Scan",
        "mcp-context-protector",
        "Promptfoo",
    ]

    @pytest.mark.parametrize("tool", OPTIONAL_TOOLS)
    def test_optional_tool_referenced(self, security_stack_content: str, tool: str):
        assert tool in security_stack_content, (
            f"Optional tool '{tool}' not referenced in security-stack.md"
        )

    @pytest.mark.parametrize("tool", PLANNED_TOOLS)
    def test_planned_tool_referenced(self, security_stack_content: str, tool: str):
        assert tool in security_stack_content, (
            f"Planned tool '{tool}' not referenced in security-stack.md"
        )


class TestSecurityRulesReferenced:
    """Verifies that key security rules are referenced."""

    SECURITY_RULES = [
        "agent-security",
        "agent-identity",
        "credential-management",
        "license-policy",
        "supply-chain-defense",
        "pentesting-readiness",
        "content-policy",
        "security-scanning",
    ]

    @pytest.mark.parametrize("rule", SECURITY_RULES)
    def test_rule_referenced(self, security_stack_content: str, rule: str):
        assert rule in security_stack_content, (
            f"Security rule '{rule}' not referenced in security-stack.md"
        )


class TestSafetyMeshCrossReference:
    """Verifies that safety-mesh.md references security-stack.md."""

    def test_safety_mesh_references_security_stack(self, safety_mesh_content: str):
        assert "security-stack.md" in safety_mesh_content, (
            "safety-mesh.md must reference security-stack.md"
        )


class TestLayerCountConsistency:
    """Verifies that layer counts in the summary match actual content."""

    def test_layer_count_in_header(self, security_stack_content: str):
        assert "Layers: 8" in security_stack_content, (
            "Header must state Layers: 8"
        )

    def test_active_layers_count(self, security_stack_content: str):
        assert "Active defense layers | 8" in security_stack_content, (
            "Summary must state 8 active defense layers"
        )

    def test_all_status_types_present(self, security_stack_content: str):
        assert "**ACTIVE**" in security_stack_content
        assert "**OPTIONAL**" in security_stack_content
        assert "**PLANNED**" in security_stack_content


class TestHooksExistOnDisk:
    """Verifies that hooks referenced as ACTIVE actually exist on disk."""

    HOOKS_THAT_MUST_EXIST = [
        "clarification-gate.sh",
        "blast-radius.sh",
        "dry-run-preview.sh",
        "rate-limiter.sh",
        "scope-proportionality.sh",
        "claim-validator.sh",
        "assumption-tracker.sh",
        "trust-score-validator.sh",
        "confidence-gate.sh",
        "clarification-interceptor.sh",
        "auto-rollback-trigger.sh",
        "content-policy.sh",
        "secret-detector.sh",
        "scope-creep-detector.sh",
    ]

    @pytest.mark.parametrize("hook_file", HOOKS_THAT_MUST_EXIST)
    def test_hook_exists_on_disk(self, hook_file: str):
        hook_path = PROJECT_ROOT / "hooks" / hook_file
        assert hook_path.exists(), (
            f"Hook '{hook_file}' is referenced as ACTIVE but does not exist at {hook_path}"
        )


class TestOptionalHooksExistOnDisk:
    """Verifies that hooks referenced as OPTIONAL exist if documented."""

    def test_aguara_hook_exists(self):
        hook_path = PROJECT_ROOT / "hooks" / "aguara-scan.sh"
        assert hook_path.exists(), (
            "Aguara hook is documented as OPTIONAL but aguara-scan.sh is missing"
        )

    def test_semgrep_hook_exists(self):
        hook_path = PROJECT_ROOT / "hooks" / "semgrep-scan.sh"
        assert hook_path.exists(), (
            "Semgrep hook is documented as OPTIONAL but semgrep-scan.sh is missing"
        )
