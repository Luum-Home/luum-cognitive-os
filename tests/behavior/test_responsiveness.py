"""Behavior tests for the responsiveness rule.

Tests verify that the responsiveness protocol exists, is properly
structured, and contains the required behavioral constraints.
"""

import pytest
from pathlib import Path

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestResponsivenessRuleExists:
    """Verify the rule file exists and is properly structured."""

    def test_rule_file_exists(self):
        rule = PROJECT_ROOT / "rules" / "responsiveness.md"
        assert rule.exists(), "rules/responsiveness.md should exist"

    def test_rule_has_title(self):
        content = (PROJECT_ROOT / "rules" / "responsiveness.md").read_text()
        assert "# Responsiveness Protocol" in content

    def test_rule_has_mandatory_behaviors(self):
        content = (PROJECT_ROOT / "rules" / "responsiveness.md").read_text()
        assert "## Mandatory Behaviors" in content

    def test_rule_has_anti_patterns(self):
        content = (PROJECT_ROOT / "rules" / "responsiveness.md").read_text()
        assert "## Anti-Patterns" in content


class TestResponsivenessConstraints:
    """Verify the rule contains specific required constraints."""

    def test_background_threshold(self):
        """Rule must specify when to use run_in_background."""
        content = (PROJECT_ROOT / "rules" / "responsiveness.md").read_text()
        assert "run_in_background" in content
        assert "5 second" in content.lower() or ">5s" in content or ">5 second" in content.lower()

    def test_agent_batch_limit(self):
        """Rule must specify max agents per sprint."""
        content = (PROJECT_ROOT / "rules" / "responsiveness.md").read_text()
        assert "10-15" in content or "10" in content
        assert "sprint" in content.lower()

    def test_silence_threshold(self):
        """Rule must specify max silence duration."""
        content = (PROJECT_ROOT / "rules" / "responsiveness.md").read_text()
        assert "10 second" in content.lower() or ">10" in content

    def test_session_state_reference(self):
        """Rule should reference session_state.py for persistence."""
        content = (PROJECT_ROOT / "rules" / "responsiveness.md").read_text()
        assert "session_state" in content

    def test_engram_save_mentioned(self):
        """Rule should mention saving to Engram before context exhaustion."""
        content = (PROJECT_ROOT / "rules" / "responsiveness.md").read_text()
        assert "Engram" in content or "engram" in content


class TestResponsivenessInCompact:
    """Verify the rule is referenced in RULES-COMPACT.md."""

    def test_in_rules_compact(self):
        compact = (PROJECT_ROOT / "rules" / "RULES-COMPACT.md").read_text()
        assert "responsiveness" in compact.lower()

    def test_compact_mentions_background(self):
        compact = (PROJECT_ROOT / "rules" / "RULES-COMPACT.md").read_text()
        assert "run_in_background" in compact

    def test_compact_mentions_agent_limit(self):
        compact = (PROJECT_ROOT / "rules" / "RULES-COMPACT.md").read_text()
        assert "10-15" in compact or "sprint" in compact.lower()
