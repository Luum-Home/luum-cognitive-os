"""Behavioral tests for skills/compat-test — ADR-059 Phase 1 pilot.

compat-test is an agent-instructional skill: it has no backing script but its
behavior is well-defined: read cognitive-os.yaml, run 8 checks, produce a
structured report. We test the _prerequisites_ the skill needs to function.
"""
from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CATALOG_MD = PROJECT_ROOT / "skills" / "CATALOG.md"
CATALOG_COMPACT_MD = PROJECT_ROOT / "skills" / "CATALOG-COMPACT.md"
COS_YAML = PROJECT_ROOT / "cognitive-os.yaml"

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 1. Imports / invocation — SKILL.md exists with required frontmatter
# ---------------------------------------------------------------------------


class TestCompatTestSkillExists:
    def test_skill_md_present(self):
        """skills/compat-test/SKILL.md must exist."""
        skill_md = PROJECT_ROOT / "skills" / "compat-test" / "SKILL.md"
        assert skill_md.exists()

    def test_skill_md_has_required_frontmatter_fields(self):
        """SKILL.md must declare name, description, and audience in frontmatter."""
        skill_md = PROJECT_ROOT / "skills" / "compat-test" / "SKILL.md"
        content = skill_md.read_text()
        for field in ("name:", "description:", "audience:"):
            assert field in content, f"Missing frontmatter field: {field}"


# ---------------------------------------------------------------------------
# 2. Contract test — compat-test Test 5 (Progressive Loading)
#    Validates that CATALOG.md token estimate < level1_budget from config
# ---------------------------------------------------------------------------


class TestCompatTestProgressiveLoadingContract:
    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_catalog_md_token_estimate_within_budget(self):
        """Test 5 from compat-test: compact catalog fits level1, full catalog fits level2.

        Level 1 loads the progressive `CATALOG-COMPACT.md` index; the full
        `CATALOG.md` is a level 2 on-demand artifact and may be larger. This
        test enforces the actual progressive-loading contract instead of
        warning on a valid full-catalog overflow.
        """
        assert CATALOG_MD.exists(), "CATALOG.md missing"
        assert CATALOG_COMPACT_MD.exists(), "CATALOG-COMPACT.md missing"
        compact_chars = len(CATALOG_COMPACT_MD.read_text())
        estimated_tokens = compact_chars / 4  # chars / 4 approximation
        full_estimated_tokens = len(CATALOG_MD.read_text()) / 4

        # Read level1_budget from cognitive-os.yaml
        assert COS_YAML.exists(), "cognitive-os.yaml missing"
        config = yaml.safe_load(COS_YAML.read_text())
        budget = (
            config.get("skills", {})
            .get("loading", {})
            .get("level1_budget", 5000)
        )
        level2_budget = (
            config.get("skills", {})
            .get("loading", {})
            .get("level2_budget", 30000)
        )
        assert estimated_tokens < budget, (
            f"CATALOG-COMPACT.md estimated tokens ({estimated_tokens:.0f}) "
            f"exceeds level1_budget ({budget}). Run scripts/generate_compact_catalog.py."
        )
        assert full_estimated_tokens < level2_budget, (
            f"CATALOG.md estimated tokens ({full_estimated_tokens:.0f}) "
            f"exceeds level2_budget ({level2_budget}). Run /catalog-full immediately."
        )

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_cognitive_os_yaml_has_required_budget_fields(self):
        """Test 7 from compat-test: monthly_limit_usd, daily_alert_usd, per_session_target_usd."""
        assert COS_YAML.exists()
        config = yaml.safe_load(COS_YAML.read_text())
        budget_section = config.get("resources", {}).get("budget", {})
        # At least one budget field must be present
        budget_keys = set(budget_section.keys())
        expected = {"monthly_limit_usd", "daily_alert_usd", "per_session_target_usd"}
        found = budget_keys & expected
        assert len(found) >= 1, (
            f"cognitive-os.yaml resources.budget missing expected fields. "
            f"Found: {budget_keys}"
        )


# ---------------------------------------------------------------------------
# 3. Happy path — compat-test Test 3 (Phase Awareness)
# ---------------------------------------------------------------------------


class TestCompatTestPhaseAwareness:
    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_project_phase_is_valid(self):
        """Test 3: cognitive-os.yaml project.phase must be one of the valid values."""
        assert COS_YAML.exists()
        config = yaml.safe_load(COS_YAML.read_text())
        phase = config.get("project", {}).get("phase", "")
        valid_phases = {"reconstruction", "stabilization", "production", "maintenance"}
        assert phase in valid_phases, (
            f"project.phase={phase!r} is not a valid phase. "
            f"Valid: {valid_phases}"
        )

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_cognitive_os_yaml_project_name_present(self):
        """validate-config check: project.name must be present."""
        config = yaml.safe_load(COS_YAML.read_text())
        name = config.get("project", {}).get("name", "")
        assert name, "project.name is missing or empty in cognitive-os.yaml"


# ---------------------------------------------------------------------------
# 4. Error handling — graceful behavior when cognitive-os.yaml is malformed
# ---------------------------------------------------------------------------


class TestCompatTestErrorHandling:
    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_malformed_yaml_raises_yaml_error(self, tmp_path: Path):
        """Reading a malformed YAML must raise an exception, not silently pass."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("project:\n  name: [unclosed\n")

        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(bad_yaml.read_text())

    def test_catalog_md_is_not_empty(self):
        """CATALOG.md must exist and have substantial content for Test 1 to work."""
        assert CATALOG_MD.exists(), "CATALOG.md missing"
        content = CATALOG_MD.read_text()
        assert len(content) > 500, (
            f"CATALOG.md appears nearly empty ({len(content)} bytes). "
            "compat-test Test 1 (skill trigger) cannot work."
        )
