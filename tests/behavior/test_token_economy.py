"""Behavior tests for the token economy system.

Validates that the token-economy rule, decomposition rule, and cost_dashboard
library exist and contain the expected structure and documentation.

Author: luum
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Rule existence
# ---------------------------------------------------------------------------


class TestTokenEconomyRule:
    """Verify the token-economy rule exists and has required content."""

    def test_token_economy_rule_exists(self):
        rule = PROJECT_ROOT / "rules" / "token-economy.md"
        assert rule.exists(), "rules/token-economy.md must exist"

    def test_rule_has_five_principles(self):
        rule = PROJECT_ROOT / "rules" / "token-economy.md"
        content = rule.read_text()
        principles = [
            "Transparency",
            "Worthiness",
            "Decomposition",
            "Memory-First",
            "Optimize by Default",
        ]
        for p in principles:
            assert p in content, f"token-economy rule must contain principle: {p}"

    def test_anti_waste_patterns_documented(self):
        rule = PROJECT_ROOT / "rules" / "token-economy.md"
        content = rule.read_text()
        assert "Anti-Waste Patterns" in content

    def test_model_downgrade_chain_documented(self):
        rule = PROJECT_ROOT / "rules" / "token-economy.md"
        content = rule.read_text()
        assert "downgrade" in content.lower()

    def test_session_cost_reporting_documented(self):
        rule = PROJECT_ROOT / "rules" / "token-economy.md"
        content = rule.read_text()
        assert "session" in content.lower()
        assert "cost" in content.lower()
        assert "report" in content.lower()


class TestDecompositionRule:
    """Verify the decomposition rule exists and has required content."""

    def test_decomposition_rule_exists(self):
        rule = PROJECT_ROOT / "rules" / "decomposition.md"
        assert rule.exists(), "rules/decomposition.md must exist"

    def test_decomposition_has_cost_thresholds(self):
        rule = PROJECT_ROOT / "rules" / "decomposition.md"
        content = rule.read_text()
        assert "$1.00" in content or "1.00" in content
        assert "$0.50" in content or "0.50" in content

    def test_decomposition_references_model_routing(self):
        rule = PROJECT_ROOT / "rules" / "decomposition.md"
        content = rule.read_text()
        assert "model-routing" in content.lower() or "Model Routing" in content


# ---------------------------------------------------------------------------
# Library importability
# ---------------------------------------------------------------------------


class TestCostDashboardLibrary:
    """Verify the cost_dashboard library is importable and functional."""

    def test_cost_dashboard_importable(self):
        from lib.cost_dashboard import CostDashboard
        assert CostDashboard is not None

    def test_record_cost_event_importable(self):
        from lib.cost_dashboard import record_cost_event
        assert callable(record_cost_event)

    def test_format_compact_status_returns_string(self, tmp_path):
        from lib.cost_dashboard import CostDashboard
        metrics = tmp_path / "cost-events.jsonl"
        dash = CostDashboard(metrics_path=str(metrics))
        result = dash.format_compact_status()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_model_prices_defined(self):
        from lib.cost_dashboard import MODEL_PRICES
        assert "opus" in MODEL_PRICES or "claude-opus-4-6" in MODEL_PRICES
        assert "sonnet" in MODEL_PRICES or "claude-sonnet-4" in MODEL_PRICES
        assert "haiku" in MODEL_PRICES or "claude-haiku-3.5" in MODEL_PRICES


# ---------------------------------------------------------------------------
# RULES-COMPACT.md integration
# ---------------------------------------------------------------------------


class TestRulesCompactIntegration:
    """Verify token economy rules are referenced in RULES-COMPACT.md."""

    def test_token_economy_in_compact_rules(self):
        compact = PROJECT_ROOT / "rules" / "RULES-COMPACT.md"
        content = compact.read_text()
        assert "token-economy" in content.lower() or "Token Economy" in content

    def test_decomposition_in_compact_rules(self):
        compact = PROJECT_ROOT / "rules" / "RULES-COMPACT.md"
        content = compact.read_text()
        assert "decomposition" in content.lower() or "Decomposition" in content
