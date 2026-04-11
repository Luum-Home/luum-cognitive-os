"""Tests for rules/response-compression.md — orchestrator output discipline."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
RULE_FILE = REPO_ROOT / "rules" / "response-compression.md"
COMPACT_FILE = REPO_ROOT / "rules" / "RULES-COMPACT.md"


def test_rule_file_exists():
    assert RULE_FILE.exists(), "rules/response-compression.md must exist"


def test_has_budget_table():
    content = RULE_FILE.read_text()
    assert "Response Budgets" in content, "Must contain 'Response Budgets' section"


def test_has_formatting_rules():
    content = RULE_FILE.read_text()
    assert "Formatting Rules" in content, "Must contain 'Formatting Rules' section"


def test_has_anti_patterns():
    content = RULE_FILE.read_text()
    assert "Anti-Patterns" in content, "Must contain 'Anti-Patterns' section"


def test_budgets_are_numeric():
    content = RULE_FILE.read_text()
    # Budget table rows should have numeric max values (e.g., | 3 | 200 |)
    numeric_budget_pattern = re.compile(r"\|\s*\d+\s*\|\s*\d+\s*\|")
    assert numeric_budget_pattern.search(content), (
        "Budget table must contain rows with numeric max lines and max chars"
    )


def test_rule_referenced_in_compact():
    content = COMPACT_FILE.read_text()
    assert "response-compression" in content, (
        "RULES-COMPACT.md must reference response-compression"
    )
