"""Unit tests for EscalationDetector.suggest_model_upgrade.

Validates the model upgrade suggestion logic: haiku->sonnet, sonnet->opus,
opus->None (human escalation), and edge cases like unknown models.

Python 3.9+ compatible.
"""

import pytest

from lib.escalation_detector import EscalationDetector

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def detector() -> EscalationDetector:
    """Return a fresh EscalationDetector."""
    return EscalationDetector()


# ---------------------------------------------------------------------------
# Tests: Upgrade chain (short names)
# ---------------------------------------------------------------------------


class TestModelUpgradeShortNames:
    """Test upgrade suggestions using short model names."""

    def test_haiku_upgrades_to_sonnet(self, detector: EscalationDetector) -> None:
        result = detector.suggest_model_upgrade("haiku", "loop_detected")
        assert result == "claude-sonnet-4"

    def test_sonnet_upgrades_to_opus(self, detector: EscalationDetector) -> None:
        result = detector.suggest_model_upgrade("sonnet", "error_repeat")
        assert result == "claude-opus-4-6"

    def test_opus_returns_none_for_human_escalation(
        self, detector: EscalationDetector
    ) -> None:
        result = detector.suggest_model_upgrade("opus", "confidence_drop")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: Upgrade chain (canonical names)
# ---------------------------------------------------------------------------


class TestModelUpgradeCanonicalNames:
    """Test upgrade suggestions using full canonical model names."""

    def test_claude_haiku_upgrades_to_claude_sonnet(
        self, detector: EscalationDetector
    ) -> None:
        result = detector.suggest_model_upgrade("claude-haiku-3.5", "no_progress")
        assert result == "claude-sonnet-4"

    def test_claude_sonnet_upgrades_to_claude_opus(
        self, detector: EscalationDetector
    ) -> None:
        result = detector.suggest_model_upgrade("claude-sonnet-4", "loop_detected")
        assert result == "claude-opus-4-6"

    def test_claude_opus_returns_none(self, detector: EscalationDetector) -> None:
        result = detector.suggest_model_upgrade("claude-opus-4-6", "error_repeat")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: Edge cases
# ---------------------------------------------------------------------------


class TestModelUpgradeEdgeCases:
    """Test edge cases: unknown models, empty strings, case sensitivity."""

    def test_unknown_model_returns_none(self, detector: EscalationDetector) -> None:
        result = detector.suggest_model_upgrade("gpt-4o", "loop_detected")
        assert result is None

    def test_empty_model_returns_none(self, detector: EscalationDetector) -> None:
        result = detector.suggest_model_upgrade("", "no_progress")
        assert result is None

    def test_case_insensitive_normalisation(
        self, detector: EscalationDetector
    ) -> None:
        """Model names should be normalised case-insensitively."""
        # The _normalise_model method lowercases before lookup.
        normalised = EscalationDetector._normalise_model("Sonnet")
        assert normalised == "sonnet"

        normalised = EscalationDetector._normalise_model("OPUS")
        assert normalised == "opus"

    def test_all_escalation_types_accepted(
        self, detector: EscalationDetector
    ) -> None:
        """suggest_model_upgrade should work with any escalation type."""
        types = [
            "loop_detected",
            "no_progress",
            "confidence_drop",
            "error_repeat",
            "timeout_risk",
        ]
        for etype in types:
            result = detector.suggest_model_upgrade("sonnet", etype)
            assert result == "claude-opus-4-6", f"Failed for escalation type: {etype}"


# ---------------------------------------------------------------------------
# Tests: Integration with escalation detection
# ---------------------------------------------------------------------------


class TestModelUpgradeIntegration:
    """Test suggest_model_upgrade in context of detected escalations."""

    def test_upgrade_after_loop_detection(self) -> None:
        """When a loop is detected with recommend severity, suggest upgrade."""
        d = EscalationDetector()
        # Trigger loop_detected at recommend level (2x threshold = 6 edits).
        for _ in range(6):
            d.record_tool_call("Edit", success=False, target_file="stuck.py")
        signal = d.check_should_escalate()
        assert signal is not None
        assert signal.severity == "recommend"

        upgrade = d.suggest_model_upgrade("sonnet", signal.type)
        assert upgrade == "claude-opus-4-6"

    def test_no_upgrade_for_suggest_severity(self) -> None:
        """When severity is only 'suggest', the caller decides whether to upgrade.
        The method itself always returns a result regardless of severity."""
        d = EscalationDetector()
        for _ in range(3):
            d.record_tool_call("Edit", success=False, target_file="minor.py")
        signal = d.check_should_escalate()
        assert signal is not None
        assert signal.severity == "suggest"

        # Method still returns a valid upgrade -- severity gating is the
        # caller's responsibility.
        upgrade = d.suggest_model_upgrade("haiku", signal.type)
        assert upgrade == "claude-sonnet-4"

    def test_opus_stuck_recommends_human(self) -> None:
        """When opus is stuck, suggest_model_upgrade returns None,
        meaning human escalation is the only option."""
        d = EscalationDetector()
        for _ in range(6):
            d.record_tool_call("Edit", success=False, target_file="hard.py")
        signal = d.check_should_escalate()
        assert signal is not None

        upgrade = d.suggest_model_upgrade("opus", signal.type)
        assert upgrade is None


# ---------------------------------------------------------------------------
# Tests: _normalise_model
# ---------------------------------------------------------------------------


class TestNormaliseModel:
    """Test the static _normalise_model helper."""

    def test_short_names(self) -> None:
        assert EscalationDetector._normalise_model("haiku") == "haiku"
        assert EscalationDetector._normalise_model("sonnet") == "sonnet"
        assert EscalationDetector._normalise_model("opus") == "opus"

    def test_canonical_names(self) -> None:
        assert EscalationDetector._normalise_model("claude-haiku-3.5") == "haiku"
        assert EscalationDetector._normalise_model("claude-sonnet-4") == "sonnet"
        assert EscalationDetector._normalise_model("claude-opus-4-6") == "opus"

    def test_non_anthropic_returns_family(self) -> None:
        # Non-Anthropic models now return their family from the catalog.
        assert EscalationDetector._normalise_model("gpt-4o") == "gpt4"
        assert EscalationDetector._normalise_model("llama-3-70b") == "llama"

    def test_unknown_returns_none(self) -> None:
        assert EscalationDetector._normalise_model("") is None
        assert EscalationDetector._normalise_model("totally-unknown-model") is None

    def test_case_insensitive(self) -> None:
        assert EscalationDetector._normalise_model("HAIKU") == "haiku"
        assert EscalationDetector._normalise_model("Claude-Sonnet-4") == "sonnet"
