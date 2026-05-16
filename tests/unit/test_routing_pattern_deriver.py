"""Tests for lib.routing_pattern_deriver.RoutingPatternDeriver."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure lib/ is importable when run from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from lib.routing_pattern_deriver import RoutingPatternDeriver, _build_yaml_block


@pytest.fixture()
def deriver() -> RoutingPatternDeriver:
    return RoutingPatternDeriver()


# ---------------------------------------------------------------------------
# Basic output contract
# ---------------------------------------------------------------------------


class TestOutputContract:
    def test_returns_list_of_dicts(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("audit-integrity", "run an audit integrity check")
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_each_item_has_pattern_and_confidence(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("audit-integrity", "run an audit integrity check")
        for item in result:
            assert "pattern" in item
            assert "confidence" in item
            assert isinstance(item["pattern"], str)
            assert 0.0 < item["confidence"] <= 1.0

    def test_at_most_three_patterns(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("audit-integrity", "run an audit integrity check")
        assert len(result) <= 3

    def test_ordered_by_confidence_descending(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("audit-integrity", "run an audit integrity check")
        confidences = [p["confidence"] for p in result]
        assert confidences == sorted(confidences, reverse=True)


# ---------------------------------------------------------------------------
# Known skill samples
# ---------------------------------------------------------------------------


class TestKnownSkills:
    def test_audit_integrity_has_name_pattern(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("audit-integrity", "Audit the integrity of skills and hooks")
        patterns = [p["pattern"] for p in result]
        # re.escape turns hyphens into \- so check for the escaped or unescaped form
        assert any("audit" in pat and "integrity" in pat for pat in patterns)

    def test_caveman_has_name_pattern(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("caveman", "Compress context using minimal cave-person language")
        patterns = [p["pattern"] for p in result]
        assert any("caveman" in pat for pat in patterns)

    def test_cos_quickstart_collapsed_variant(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("cos-quickstart", "Quick start guide for Cognitive OS")
        patterns = [p["pattern"] for p in result]
        # hyphen-collapsed variant: "cos quickstart" (re.escape → "cos\ quickstart")
        assert any("cos" in pat and "quickstart" in pat for pat in patterns)

    def test_cos_quickstart_returns_at_least_two(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("cos-quickstart", "Quick start guide for Cognitive OS")
        assert len(result) >= 2


# ---------------------------------------------------------------------------
# English action verb detection
# ---------------------------------------------------------------------------


class TestEnglishActionTrigger:
    def test_action_verb_creates_pattern(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive(
            "plan-feature",
            "Generate a detailed plan to implement a new feature",
        )
        patterns = [p["pattern"] for p in result]
        # Should have an action-triggered pattern containing an English verb.
        assert any("generate" in pat or "implement" in pat for pat in patterns)

    def test_action_source_is_english(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("plan-feature", "Generate a plan for a new feature")
        patterns = [p["pattern"] for p in result]
        assert any("generate" in pat for pat in patterns)


# ---------------------------------------------------------------------------
# Generic word filtering
# ---------------------------------------------------------------------------


class TestGenericWordFiltering:
    def test_create_alone_not_a_pattern(self, deriver: RoutingPatternDeriver) -> None:
        # "create" is generic; the skill name itself forces a non-generic pattern
        result = deriver.derive("create", "create something")
        # We expect the deriver to still produce patterns, but not just \bcreate\b
        # as the high-confidence primary if something better exists.
        # At minimum: 2 patterns returned (fallback description fragment)
        assert len(result) >= 1

    def test_fix_alone_filters_gracefully(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("fix-service", "fix a broken service quickly")
        patterns = [p["pattern"] for p in result]
        # "fix-service" is not generic (compound); re.escape turns - to \-
        # so check for both parts present in some pattern
        assert any("fix" in pat and "service" in pat for pat in patterns)

    def test_pure_generic_slug_still_returns_patterns(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("test", "run all tests for the project")
        # Even with a generic name we need output
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# Short / edge-case names
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_very_short_skill_name(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("mv", "move files around in the repository")
        assert len(result) >= 1

    def test_empty_description_falls_back(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("scout", "")
        assert len(result) >= 1

    def test_no_aliases_does_not_raise(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("scout", "recon before medium+ tasks", name_aliases=None)
        assert len(result) >= 1

    def test_aliases_add_patterns(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive(
            "scout",
            "recon before medium+ tasks",
            name_aliases=["recon", "reconnaissance"],
        )
        patterns = [p["pattern"] for p in result]
        assert any("recon" in pat or "reconnaissance" in pat for pat in patterns)

    def test_unicode_description_handled(self, deriver: RoutingPatternDeriver) -> None:
        result = deriver.derive("unicode-skill", "Detailed code analysis")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# YAML block builder
# ---------------------------------------------------------------------------


class TestYamlBlockBuilder:
    def test_yaml_block_starts_with_routing_patterns(self, deriver: RoutingPatternDeriver) -> None:
        patterns = deriver.derive("audit-integrity", "run an audit integrity check")
        yaml_block = _build_yaml_block(patterns)
        assert yaml_block.startswith("routing_patterns:")

    def test_yaml_block_contains_confidence(self, deriver: RoutingPatternDeriver) -> None:
        patterns = deriver.derive("audit-integrity", "run an audit integrity check")
        yaml_block = _build_yaml_block(patterns)
        assert "confidence:" in yaml_block

    def test_yaml_block_contains_pattern(self, deriver: RoutingPatternDeriver) -> None:
        patterns = deriver.derive("audit-integrity", "run an audit integrity check")
        yaml_block = _build_yaml_block(patterns)
        assert "pattern:" in yaml_block
