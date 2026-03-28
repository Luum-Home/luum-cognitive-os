"""Unit tests for rules/context7-auto-trigger.md

Validates that the Context7 auto-trigger rule file exists and contains
the required sections for library documentation lookup.
"""

import os

import pytest

pytestmark = pytest.mark.unit

RULE_PATH = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    os.pardir,
    "rules",
    "context7-auto-trigger.md",
)


@pytest.fixture
def rule_content():
    """Read the rule file content once for all tests."""
    with open(RULE_PATH, "r") as f:
        return f.read()


class TestContext7Rule:
    """Tests for the Context7 auto-trigger rule file."""

    def test_rule_file_exists(self):
        """Verify rules/context7-auto-trigger.md exists."""
        assert os.path.isfile(RULE_PATH), (
            f"Rule file not found at {RULE_PATH}"
        )

    def test_rule_mentions_context7(self, rule_content):
        """Content references Context7 MCP."""
        assert "Context7" in rule_content, (
            "Rule must reference Context7"
        )
        assert "MCP" in rule_content, (
            "Rule must reference MCP (Model Context Protocol)"
        )

    def test_rule_mentions_caching(self, rule_content):
        """Content references Engram caching for library docs."""
        assert "Caching" in rule_content, (
            "Rule must have a Caching section"
        )
        assert "Engram" in rule_content, (
            "Rule must reference Engram for caching"
        )
        assert "docs/libraries/" in rule_content, (
            "Rule must specify the Engram topic key prefix for library docs"
        )

    def test_rule_mentions_graceful_degradation(self, rule_content):
        """Content has a graceful degradation section."""
        assert "Graceful Degradation" in rule_content, (
            "Rule must have a Graceful Degradation section"
        )
        assert "unavailable" in rule_content.lower(), (
            "Graceful degradation must address Context7 unavailability"
        )
        assert "Trust Report" in rule_content, (
            "Graceful degradation must mention noting uncertainty in Trust Report"
        )
