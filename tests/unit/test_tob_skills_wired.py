"""Unit tests verifying Trail of Bits security skills are wired into the routing system.

These tests do NOT require the git submodule to be present.  They validate that:
- The expected submodule path is documented and referenced correctly.
- The five priority skills appear in CATALOG.md.
- The five priority skills appear in the skill routing table in skill-management.md.

If the submodule IS present the tests additionally verify that the skills exist on disk.
"""
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

SUBMODULE_PATH = PROJECT_ROOT / ".claude" / "plugins" / "trailofbits-skills"

# Five priority skills that must be wired in
TOB_SKILLS = [
    "tob-agentic-actions-auditor",
    "tob-supply-chain-risk-auditor",
    "tob-static-analysis",
    "tob-insecure-defaults",
    "tob-variant-analysis",
]

# Routing signals that must appear in skill-management.md
TOB_ROUTING_SIGNALS = [
    "trail of bits",
    "tob audit",
    "agentic actions",
    "supply chain audit",
    "insecure defaults",
    "variant analysis",
]


# ---------------------------------------------------------------------------
# Catalog tests
# ---------------------------------------------------------------------------


class TestTobSkillsInCatalog:
    """Verify the five priority ToB skills are listed in CATALOG.md."""

    @pytest.fixture(scope="class")
    def catalog_text(self) -> str:
        catalog = PROJECT_ROOT / "skills" / "CATALOG.md"
        assert catalog.exists(), f"CATALOG.md not found at {catalog}"
        return catalog.read_text()

    @pytest.mark.parametrize("skill_name", TOB_SKILLS)
    def test_skill_in_catalog(self, catalog_text, skill_name):
        """Each priority ToB skill must appear in CATALOG.md."""
        assert skill_name in catalog_text, (
            f"'{skill_name}' not found in skills/CATALOG.md — "
            "add it to the 'External Skills — Trail of Bits' section"
        )

    def test_tob_section_header_present(self, catalog_text):
        """CATALOG.md must contain a dedicated Trail of Bits section."""
        assert "Trail of Bits" in catalog_text, (
            "No 'Trail of Bits' section found in CATALOG.md"
        )

    def test_submodule_path_documented(self, catalog_text):
        """CATALOG.md must document the submodule installation path."""
        assert ".claude/plugins/trailofbits-skills" in catalog_text, (
            "Submodule path '.claude/plugins/trailofbits-skills' not referenced in CATALOG.md"
        )

    def test_license_documented(self, catalog_text):
        """CATALOG.md must document the CC-BY-SA-4.0 license requirement."""
        assert "CC-BY-SA-4.0" in catalog_text, (
            "CC-BY-SA-4.0 license not mentioned in CATALOG.md ToB section"
        )


# ---------------------------------------------------------------------------
# Routing table tests
# ---------------------------------------------------------------------------


class TestTobSkillsInRouting:
    """Verify key ToB skills appear in the skill routing table."""

    @pytest.fixture(scope="class")
    def routing_text(self) -> str:
        routing = PROJECT_ROOT / "rules" / "skill-management.md"
        assert routing.exists(), f"skill-management.md not found at {routing}"
        return routing.read_text()

    @pytest.mark.parametrize("skill_name", TOB_SKILLS)
    def test_skill_in_routing(self, routing_text, skill_name):
        """Each priority ToB skill must appear in the routing table."""
        assert skill_name in routing_text, (
            f"'{skill_name}' not found in rules/skill-management.md routing table"
        )

    @pytest.mark.parametrize("signal", TOB_ROUTING_SIGNALS)
    def test_routing_signal_present(self, routing_text, signal):
        """Each routing trigger phrase must appear in the routing table."""
        assert signal in routing_text, (
            f"Routing signal '{signal}' not found in rules/skill-management.md — "
            "users won't be able to trigger this skill by natural language"
        )


# ---------------------------------------------------------------------------
# Install script tests
# ---------------------------------------------------------------------------


class TestInstallScript:
    """Verify the install script references the correct submodule path."""

    @pytest.fixture(scope="class")
    def install_script_text(self) -> str:
        script = PROJECT_ROOT / "scripts" / "install-tob-skills.sh"
        assert script.exists(), f"install-tob-skills.sh not found at {script}"
        return script.read_text()

    def test_script_references_submodule_path(self, install_script_text):
        """Install script must reference the canonical submodule path."""
        assert ".claude/plugins/trailofbits-skills" in install_script_text

    def test_script_uses_git_submodule_add(self, install_script_text):
        """Install script must use git submodule add."""
        assert "git submodule add" in install_script_text

    def test_script_references_upstream_repo(self, install_script_text):
        """Install script must reference the Trail of Bits GitHub repo."""
        assert "trailofbits/skills" in install_script_text


# ---------------------------------------------------------------------------
# Disk presence tests (skipped when submodule is absent)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not SUBMODULE_PATH.exists(),
    reason=(
        "Trail of Bits submodule not installed — "
        "run 'bash scripts/install-tob-skills.sh' to install"
    ),
)
class TestTobSkillsOnDisk:
    """Verify skill files exist on disk when the submodule is present."""

    # Map our routing aliases to the upstream directory names used by Trail of Bits
    UPSTREAM_NAMES = {
        "tob-agentic-actions-auditor": "agentic-actions-auditor",
        "tob-supply-chain-risk-auditor": "supply-chain-risk-auditor",
        "tob-static-analysis": "static-analysis",
        "tob-insecure-defaults": "insecure-defaults",
        "tob-variant-analysis": "variant-analysis",
    }

    @pytest.mark.parametrize("skill_alias,upstream_name", UPSTREAM_NAMES.items())
    def test_skill_directory_exists(self, skill_alias, upstream_name):
        """Each priority skill directory must exist inside the submodule."""
        skill_dir = SUBMODULE_PATH / upstream_name
        assert skill_dir.exists(), (
            f"Expected skill directory '{upstream_name}' not found inside "
            f"{SUBMODULE_PATH} (routing alias: {skill_alias})"
        )

    def test_submodule_not_empty(self):
        """Submodule directory must contain files (not an empty clone stub)."""
        contents = list(SUBMODULE_PATH.iterdir())
        assert len(contents) > 0, (
            f"Submodule at {SUBMODULE_PATH} appears to be empty — "
            "run 'git submodule update --init'"
        )
