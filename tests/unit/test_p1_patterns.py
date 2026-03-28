"""Tests for P1 patterns: compound skill, task claiming, branch-aware Engram."""
import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


class TestCompoundSkill:
    def test_skill_exists(self):
        assert Path("skills/sdd-compound/SKILL.md").exists()

    def test_skill_has_frontmatter(self):
        content = Path("skills/sdd-compound/SKILL.md").read_text()
        assert "name: sdd-compound" in content
        assert "mem_save" in content

    def test_skill_mentions_archive(self):
        content = Path("skills/sdd-compound/SKILL.md").read_text()
        assert "archive" in content.lower()


class TestTaskClaiming:
    def test_fault_tolerance_mentions_claiming(self):
        content = Path("rules/fault-tolerance.md").read_text()
        assert "claimed_by" in content or "claim" in content.lower()


class TestBranchAwareEngram:
    def test_engram_org_mentions_branch(self):
        content = Path("rules/engram-organization.md").read_text()
        assert "@branch" in content or "Branch-Aware" in content
