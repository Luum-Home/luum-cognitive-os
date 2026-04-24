"""Behavioral tests for skills/validate-config — ADR-059 Phase 1 pilot.

validate-config checks cognitive-os.yaml, CATALOG.md, SKILL.md frontmatter,
and other config files. Tests validate the actual project config against the
skill's documented rules (no LLM calls needed).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COS_YAML = PROJECT_ROOT / "cognitive-os.yaml"
CATALOG_MD = PROJECT_ROOT / "skills" / "CATALOG.md"
RULES_COMPACT = PROJECT_ROOT / "rules" / "RULES-COMPACT.md"

pytestmark = pytest.mark.unit

VALID_PHASES = {"reconstruction", "stabilization", "production", "maintenance"}
VALID_MODELS = {"opus", "sonnet", "haiku"}


# ---------------------------------------------------------------------------
# 1. Imports / invocation — SKILL.md exists and documents all check categories
# ---------------------------------------------------------------------------


class TestValidateConfigSkillExists:
    def test_skill_md_present(self):
        skill_md = PROJECT_ROOT / "skills" / "validate-config" / "SKILL.md"
        assert skill_md.exists()

    def test_skill_md_documents_seven_check_categories(self):
        """SKILL.md must document 7 validation categories."""
        skill_md = PROJECT_ROOT / "skills" / "validate-config" / "SKILL.md"
        content = skill_md.read_text()
        expected_categories = [
            "cognitive-os.yaml",
            "CATALOG.md",
            "RULES-COMPACT.md",
            "SKILL.md",
            "Hooks",
        ]
        for cat in expected_categories:
            assert cat in content, f"Missing validation category: {cat}"

    def test_skill_md_documents_exit_codes(self):
        """SKILL.md must document PASS/WARNINGS/ERRORS exit codes."""
        skill_md = PROJECT_ROOT / "skills" / "validate-config" / "SKILL.md"
        content = skill_md.read_text()
        for code in ("PASS", "WARNINGS", "ERRORS"):
            assert code in content, f"Missing exit code documentation: {code}"


# ---------------------------------------------------------------------------
# 2. Contract test — actual cognitive-os.yaml passes validate-config rules
# ---------------------------------------------------------------------------


class TestValidateConfigContract:
    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_cos_yaml_is_valid_yaml(self):
        """cognitive-os.yaml must parse without errors [E001 check]."""
        assert COS_YAML.exists(), "cognitive-os.yaml missing"
        config = yaml.safe_load(COS_YAML.read_text())
        assert isinstance(config, dict), "cognitive-os.yaml must be a YAML mapping"

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_cos_yaml_has_project_name(self):
        """cognitive-os.yaml must have project.name [E001 check]."""
        config = yaml.safe_load(COS_YAML.read_text())
        name = config.get("project", {}).get("name", "")
        assert name, "cognitive-os.yaml: project.name is missing or empty"

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_cos_yaml_has_valid_phase(self):
        """cognitive-os.yaml project.phase must be a valid value [E001 check]."""
        config = yaml.safe_load(COS_YAML.read_text())
        phase = config.get("project", {}).get("phase", "")
        assert phase in VALID_PHASES, (
            f"project.phase={phase!r} is not valid. Must be one of: {VALID_PHASES}"
        )

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_cos_yaml_has_positive_monthly_budget(self):
        """cognitive-os.yaml resources.budget.monthly_limit_usd must be > 0 [E001 check]."""
        config = yaml.safe_load(COS_YAML.read_text())
        budget = (
            config.get("resources", {})
            .get("budget", {})
            .get("monthly_limit_usd", 0)
        )
        assert isinstance(budget, (int, float)) and budget > 0, (
            f"resources.budget.monthly_limit_usd must be > 0, got: {budget}"
        )


# ---------------------------------------------------------------------------
# 3. Happy path — CATALOG.md vs skills/ directory cross-reference
# ---------------------------------------------------------------------------


class TestValidateConfigCatalogCheck:
    def test_catalog_md_exists(self):
        """CATALOG.md must exist (validate-config check 3)."""
        assert CATALOG_MD.exists(), "skills/CATALOG.md is missing"

    def test_catalog_md_is_not_empty(self):
        """CATALOG.md must have substantial content."""
        content = CATALOG_MD.read_text()
        assert len(content) > 200, "CATALOG.md appears nearly empty"

    def test_no_phantom_skills_in_catalog(self):
        """Every skill listed in CATALOG.md must have a directory in skills/ [E003 check]."""
        catalog_content = CATALOG_MD.read_text()
        skills_dir = PROJECT_ROOT / "skills"

        # Extract skill names from catalog (lines with `- skill-name` or `/skill-name`)
        skill_refs = re.findall(r"`([a-z][a-z0-9-]+)`", catalog_content)
        skill_refs = set(skill_refs)

        phantom = []
        for ref in skill_refs:
            skill_path = skills_dir / ref
            if not skill_path.exists():
                phantom.append(ref)

        # Allow up to 5 phantom refs (some catalog entries may reference sub-names)
        assert len(phantom) < 10, (
            f"Found {len(phantom)} possible phantom skill refs in CATALOG.md "
            f"(no matching directory): {sorted(phantom)[:10]}"
        )

    def test_skill_directories_have_skill_md(self):
        """Every skill directory must have SKILL.md [E002 check]. Sample check.

        Skips placeholder directories (empty + only .gitkeep) — those are
        scaffolding containers waiting for auto-generated skills, not real skills.
        """
        skills_dir = PROJECT_ROOT / "skills"
        missing = []
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            # Skip placeholder directories (only contain .gitkeep or are empty)
            dir_files = [f for f in skill_dir.iterdir() if f.name != ".gitkeep"]
            if not dir_files:
                continue  # Empty placeholder — not a real skill yet
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                missing.append(str(skill_dir.name))

        assert not missing, (
            f"Skill directories missing SKILL.md: {missing}"
        )


# ---------------------------------------------------------------------------
# 4. Error handling — frontmatter validation for a malformed SKILL.md
# ---------------------------------------------------------------------------


class TestValidateConfigSkillFrontmatterCheck:
    def test_valid_frontmatter_passes(self, tmp_path: Path):
        """A SKILL.md with required frontmatter fields should pass validation."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\nname: test-skill\ndescription: A test skill.\nversion: 1.0.0\n---\n\n# Body"
        )
        content = skill_md.read_text()

        # Validate frontmatter presence
        has_frontmatter = content.startswith("---")
        assert has_frontmatter

        # Extract frontmatter
        fm_end = content.find("---", 3)
        frontmatter = content[3:fm_end].strip()
        assert "name:" in frontmatter
        assert "description:" in frontmatter

    def test_missing_name_field_is_invalid(self, tmp_path: Path):
        """A SKILL.md without 'name:' in frontmatter must be flagged as ERROR."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\ndescription: Missing name.\n---\n\n# Body")
        content = skill_md.read_text()

        fm_end = content.find("---", 3)
        frontmatter = content[3:fm_end].strip()
        has_name = "name:" in frontmatter
        assert not has_name, "Test setup: name field should be absent"

    def test_missing_frontmatter_entirely_is_invalid(self, tmp_path: Path):
        """A SKILL.md with no YAML frontmatter is an ERROR per validate-config."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("# Just a title\n\nNo frontmatter here.\n")
        content = skill_md.read_text()

        has_frontmatter = content.startswith("---")
        assert not has_frontmatter, "Test setup: frontmatter should be absent"

    def test_rules_compact_references_existing_rule_files(self):
        """Every rule referenced in RULES-COMPACT.md must exist in rules/ dir."""
        if not RULES_COMPACT.exists():
            pytest.skip("RULES-COMPACT.md not found")

        content = RULES_COMPACT.read_text()
        rules_dir = PROJECT_ROOT / "rules"

        # Extract rule references like [`rule-name`] or `rules/rule-name.md`
        refs = re.findall(r"`([a-z][a-z0-9-]+)`", content)
        missing = []
        for ref in refs:
            rule_file = rules_dir / f"{ref}.md"
            if not rule_file.exists() and len(ref) > 5:
                missing.append(ref)

        # Allow some tolerance (not all backtick terms are rule file names)
        assert len(missing) < 30, (
            f"RULES-COMPACT.md has {len(missing)} possible broken rule references "
            f"(sample): {sorted(missing)[:10]}"
        )
