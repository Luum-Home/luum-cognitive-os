"""Tests for component classification skill and rule."""
import pytest
from pathlib import Path

pytestmark = pytest.mark.unit

class TestClassifierSkill:
    def test_skill_exists(self):
        assert Path("skills/component-classifier/SKILL.md").exists()

    def test_skill_has_decision_tree(self):
        content = Path("skills/component-classifier/SKILL.md").read_text()
        assert "decision tree" in content.lower() or "Decision Tree" in content

    def test_skill_has_output_format(self):
        content = Path("skills/component-classifier/SKILL.md").read_text()
        assert "CLASSIFICATION:" in content
        assert "CORE" in content and "PACKAGE" in content

class TestClassificationRule:
    def test_rule_exists(self):
        assert Path("rules/component-classification.md").exists()

    def test_rule_mentions_versioning(self):
        content = Path("rules/component-classification.md").read_text()
        assert "semver" in content.lower() or "version" in content.lower()

    def test_rule_mentions_cos_version(self):
        content = Path("rules/component-classification.md").read_text()
        assert "cos_version" in content

    def test_rule_has_criteria_table(self):
        content = Path("rules/component-classification.md").read_text()
        assert "CORE" in content and "PACKAGE" in content
        assert "External tool" in content or "external tool" in content

class TestAuditDocument:
    def test_audit_exists(self):
        assert Path("docs/component-audit.md").exists()

    def test_audit_has_summary_table(self):
        content = Path("docs/component-audit.md").read_text()
        assert "375" in content or "CORE" in content
