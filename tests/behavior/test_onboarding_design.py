"""Behavior tests for the onboarding wizard design document.

Validates that docs/onboarding-wizard-design.md is comprehensive:
covers all 8+ phases, references all component types (rules, hooks,
skills, packages), includes detection logic, summary with token
overhead estimate, security profiles, Docker services, and registries.

Related files:
  - docs/onboarding-wizard-design.md (the design document)
  - scripts/cos-init.sh (existing bootstrap script)
  - scripts/set-security-profile.sh (security profile switcher)
  - cognitive-os.yaml (full configuration reference)
  - docker-compose.cognitive-os.yml (Docker service definitions)

Author: luum
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DESIGN_DOC = PROJECT_ROOT / "docs" / "onboarding-wizard-design.md"


# ── Document existence ─────────────────────────────────────────────


class TestDesignDocExists:
    """The design document must exist and be non-trivial."""

    def test_design_doc_exists(self):
        assert DESIGN_DOC.exists(), (
            "docs/onboarding-wizard-design.md must exist"
        )

    def test_design_doc_is_not_empty(self):
        assert DESIGN_DOC.exists()
        content = DESIGN_DOC.read_text()
        assert len(content) > 5000, (
            "Design doc should be substantial (>5K chars), "
            f"got {len(content)} chars"
        )

    def test_design_doc_has_title(self):
        content = DESIGN_DOC.read_text()
        assert "# Onboarding Wizard" in content or "# Wizard" in content, (
            "Design doc should have a clear title"
        )


# ── Phase coverage ─────────────────────────────────────────────────


class TestWizardPhases:
    """The wizard must document all phases of the setup flow."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text()

    def test_has_detection_phase(self):
        """Phase 1: Automatic environment detection."""
        assert re.search(
            r"(?i)phase\s*1.*detection|detection.*phase", self.content
        ), "Must document Phase 1: Detection (automatic)"

    def test_has_core_configuration_phase(self):
        """Phase 2: Core questions (scope, phase, profiles)."""
        assert re.search(
            r"(?i)phase\s*2.*core|core.*configur", self.content
        ), "Must document Phase 2: Core Configuration"

    def test_has_feature_selection_phase(self):
        """Phase 3: Feature toggles."""
        assert re.search(
            r"(?i)phase\s*3.*feature|feature.*select", self.content
        ), "Must document Phase 3: Feature Selection"

    def test_has_security_tools_phase(self):
        """Phase 4: Optional security tool installation."""
        assert re.search(
            r"(?i)phase\s*4.*security|security.*tool", self.content
        ), "Must document Phase 4: Security Tools"

    def test_has_infrastructure_phase(self):
        """Phase 5: Docker service configuration."""
        assert re.search(
            r"(?i)phase\s*5.*infra|docker.*service", self.content
        ), "Must document Phase 5: Infrastructure (Docker)"

    def test_has_registries_phase(self):
        """Phase 6: Package registry configuration."""
        assert re.search(
            r"(?i)phase\s*6.*registr|registr.*phase", self.content
        ), "Must document Phase 6: Package Registries"

    def test_has_git_integration_phase(self):
        """Phase 7: Git hooks and auto-update."""
        assert re.search(
            r"(?i)phase\s*7.*git|auto.update|pre.commit", self.content
        ), "Must document Phase 7: Git Integration"

    def test_has_summary_phase(self):
        """Final phase: Summary and install confirmation."""
        assert re.search(
            r"(?i)summary.*install|install.*summary", self.content
        ), "Must document a Summary/Install phase"

    def test_has_at_least_8_phases(self):
        """Wizard should cover at least 8 distinct phases."""
        phase_matches = re.findall(r"(?i)###?\s*phase\s*\d+", self.content)
        assert len(phase_matches) >= 8, (
            f"Expected at least 8 phases, found {len(phase_matches)}: "
            f"{phase_matches}"
        )


# ── Component type coverage ────────────────────────────────────────


class TestComponentCoverage:
    """The design must reference all COS component types."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text()

    def test_references_rules(self):
        """Must mention rules and their counts."""
        assert "rule" in self.content.lower(), (
            "Design must reference rules"
        )
        # Should mention a rule count (e.g., "92 rules")
        assert re.search(r"\d+\s*rules?", self.content, re.IGNORECASE), (
            "Design should mention a numeric rule count"
        )

    def test_references_hooks(self):
        """Must mention hooks and their registration."""
        assert "hook" in self.content.lower(), (
            "Design must reference hooks"
        )
        assert re.search(r"\d+\s*hooks?", self.content, re.IGNORECASE), (
            "Design should mention a numeric hook count"
        )

    def test_references_skills(self):
        """Must mention skills."""
        assert "skill" in self.content.lower(), (
            "Design must reference skills"
        )
        assert re.search(r"\d+\s*skills?", self.content, re.IGNORECASE), (
            "Design should mention a numeric skill count"
        )

    def test_references_packages(self):
        """Must mention packages."""
        assert "package" in self.content.lower(), (
            "Design must reference packages"
        )
        assert re.search(r"\d+\s*(?:optional\s+)?packages?", self.content, re.IGNORECASE), (
            "Design should mention a numeric package count"
        )

    def test_references_templates(self):
        """Must mention templates."""
        assert "template" in self.content.lower(), (
            "Design must reference templates"
        )


# ── Detection section ──────────────────────────────────────────────


class TestDetectionSection:
    """Phase 1 detection must cover key project signals."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text()

    def test_detects_go(self):
        assert "go.mod" in self.content, "Must detect Go projects via go.mod"

    def test_detects_node(self):
        assert "package.json" in self.content, (
            "Must detect Node/TS projects via package.json"
        )

    def test_detects_python(self):
        assert "pyproject.toml" in self.content or "requirements.txt" in self.content, (
            "Must detect Python projects"
        )

    def test_detects_rust(self):
        assert "Cargo.toml" in self.content, "Must detect Rust projects"

    def test_detects_docker(self):
        assert re.search(r"(?i)docker.*availab|detect.*docker", self.content), (
            "Must detect Docker availability"
        )

    def test_detects_git(self):
        assert re.search(r"(?i)git.*repo|\.git", self.content), (
            "Must detect git repository"
        )

    def test_detects_cicd(self):
        assert re.search(
            r"(?i)ci/?cd|github.actions|gitlab|jenkins", self.content
        ), "Must detect CI/CD systems"

    def test_detects_existing_tests(self):
        assert re.search(
            r"(?i)existing.*test|test.*framework|pytest|jest", self.content
        ), "Must detect existing test infrastructure"

    def test_detects_existing_claude_dir(self):
        assert re.search(r"(?i)\.claude|existing.*install", self.content), (
            "Must detect existing .claude/ directory"
        )


# ── Summary section ────────────────────────────────────────────────


class TestSummarySection:
    """The summary phase must include key metrics."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text()

    def test_has_token_overhead_estimate(self):
        """Summary must estimate context window impact."""
        assert re.search(
            r"(?i)token.*overhead|overhead.*token|context.*window",
            self.content,
        ), "Summary must include token overhead estimate"

    def test_mentions_percentage_of_context(self):
        """Should express overhead as percentage of context window."""
        assert re.search(r"\d+%.*context|context.*\d+%", self.content), (
            "Should express token overhead as percentage of context window"
        )

    def test_has_installation_steps(self):
        """Must describe what the installer does."""
        assert re.search(
            r"(?i)install.*step|creating.*director|generating.*yaml",
            self.content,
        ), "Must describe installation steps"

    def test_has_quick_start_commands(self):
        """Post-install quick start commands."""
        assert re.search(
            r"(?i)quick\s*start|cos\s+status|getting.started", self.content
        ), "Must include quick start commands after install"


# ── Security profiles ──────────────────────────────────────────────


class TestSecurityProfiles:
    """Must document all three security profiles."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text().lower()

    def test_references_minimal_profile(self):
        assert "minimal" in self.content, (
            "Must reference minimal security profile"
        )

    def test_references_standard_profile(self):
        assert "standard" in self.content, (
            "Must reference standard security profile"
        )

    def test_references_paranoid_profile(self):
        assert "paranoid" in self.content, (
            "Must reference paranoid security profile"
        )

    def test_profiles_have_hook_counts(self):
        """Each profile should mention its hook count."""
        content = DESIGN_DOC.read_text()
        # Should have at least 2 different hook counts for profiles
        hook_counts = re.findall(r"(\d+)\s*hooks?", content, re.IGNORECASE)
        assert len(hook_counts) >= 2, (
            "Security profiles should mention hook counts for each level"
        )


# ── Docker services ────────────────────────────────────────────────


class TestDockerServices:
    """Must document key Docker services available for configuration."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text().lower()

    def test_references_langfuse(self):
        assert "langfuse" in self.content, "Must mention Langfuse service"

    def test_references_litellm(self):
        assert "litellm" in self.content, "Must mention LiteLLM service"

    def test_references_nemo_guardrails(self):
        assert "nemo" in self.content or "guardrails" in self.content, (
            "Must mention NeMo Guardrails service"
        )

    def test_references_valkey(self):
        assert "valkey" in self.content, "Must mention Valkey service"

    def test_references_smart_start(self):
        assert "smart start" in self.content or "smart_start" in self.content, (
            "Must mention Smart Start (lazy Docker loading)"
        )

    def test_references_docker_profiles(self):
        content = DESIGN_DOC.read_text()
        assert re.search(
            r"(?i)docker.*profile|profile.*docker|observability|memory",
            content,
        ), "Must mention Docker Compose profiles"


# ── Package registries ─────────────────────────────────────────────


class TestRegistries:
    """Must document package registry configuration."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text().lower()

    def test_references_cos_official(self):
        assert "cos-official" in self.content, (
            "Must mention cos-official registry"
        )

    def test_references_luum_org(self):
        assert "luum-org" in self.content or "luum" in self.content, (
            "Must mention luum-org registry"
        )

    def test_references_local_registry(self):
        assert "local" in self.content, "Must mention local package registry"

    def test_references_garagon(self):
        assert "garagon" in self.content, (
            "Must mention garagon-tools registry"
        )

    def test_references_antigravity(self):
        assert "antigravity" in self.content, (
            "Must mention antigravity community skills"
        )

    def test_references_trail_of_bits(self):
        assert "trail of bits" in self.content or "trailofbits" in self.content, (
            "Must mention Trail of Bits skills"
        )


# ── Project phases ─────────────────────────────────────────────────


class TestProjectPhases:
    """Must document all 4 project phases as wizard options."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text().lower()

    def test_references_reconstruction(self):
        assert "reconstruction" in self.content

    def test_references_stabilization(self):
        assert "stabilization" in self.content

    def test_references_production(self):
        assert "production" in self.content

    def test_references_maintenance(self):
        assert "maintenance" in self.content


# ── Capability levels ──────────────────────────────────────────────


class TestCapabilityLevels:
    """Must document model capability levels."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text()

    def test_references_capability_levels(self):
        assert re.search(
            r"(?i)capability.*level|level.*\d.*auto.disab", self.content
        ), "Must reference capability levels"

    def test_mentions_level_3_default(self):
        assert re.search(
            r"(?i)level\s*3.*excellent|excellent.*level\s*3", self.content
        ), "Level 3 (Excellent) should be documented as default"


# ── Configuration mapping ──────────────────────────────────────────


class TestConfigMapping:
    """Wizard choices must map to cognitive-os.yaml paths."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text()

    def test_references_cognitive_os_yaml(self):
        assert "cognitive-os.yaml" in self.content, (
            "Must reference cognitive-os.yaml as the config target"
        )

    def test_references_settings_json(self):
        assert "settings.json" in self.content, (
            "Must reference .claude/settings.json for hook registration"
        )

    def test_documents_yaml_paths(self):
        """Must show specific YAML paths affected by choices."""
        assert re.search(
            r"project\.phase|efficiency\.profile|model_capability\.level",
            self.content,
        ), "Must document specific YAML config paths"


# ── Relationship to existing scripts ───────────────────────────────


class TestExistingScripts:
    """Must document relationship to existing scripts."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text()

    def test_references_cos_init(self):
        assert "cos-init" in self.content, (
            "Must reference existing cos-init.sh script"
        )

    def test_references_set_security_profile(self):
        assert "set-security-profile" in self.content, (
            "Must reference set-security-profile.sh"
        )

    def test_references_uninstall(self):
        assert "uninstall" in self.content, (
            "Must reference uninstall capability"
        )

    def test_references_upgrade(self):
        assert "upgrade" in self.content, (
            "Must reference upgrade path"
        )


# ── TUI library recommendation ─────────────────────────────────────


class TestTUILibrary:
    """Must recommend a TUI library for implementation."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text().lower()

    def test_recommends_bubbletea(self):
        assert "bubbletea" in self.content, (
            "Must recommend bubbletea (Go TUI library)"
        )

    def test_mentions_web_alternative(self):
        content = DESIGN_DOC.read_text()
        assert re.search(r"(?i)web.*wizard|web.*based|future.*web", content), (
            "Must mention future web-based wizard option"
        )


# ── Security tools ─────────────────────────────────────────────────


class TestSecurityTools:
    """Must document optional security tool installation."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text().lower()

    def test_references_aguara(self):
        assert "aguara" in self.content, "Must mention Aguara scanner"

    def test_references_semgrep(self):
        assert "semgrep" in self.content, "Must mention Semgrep SAST"

    def test_references_mcp_scan(self):
        assert "mcp-scan" in self.content or "mcp scan" in self.content, (
            "Must mention MCP-Scan"
        )

    def test_references_promptfoo(self):
        assert "promptfoo" in self.content, "Must mention Promptfoo"

    def test_references_garak(self):
        assert "garak" in self.content, "Must mention Garak"

    def test_references_parry(self):
        assert "parry" in self.content, "Must mention Parry Guard"


# ── Non-interactive and preset modes ───────────────────────────────


class TestNonInteractiveMode:
    """Must support non-interactive installation."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = DESIGN_DOC.read_text()

    def test_has_non_interactive_mode(self):
        assert re.search(
            r"(?i)non.interactive|--non-interactive|cli.*mode", self.content
        ), "Must document non-interactive mode"

    def test_has_preset_configurations(self):
        assert re.search(r"(?i)preset|--preset", self.content), (
            "Must document preset configurations"
        )
