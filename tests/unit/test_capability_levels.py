"""Unit tests for lib/capability_levels.py

Validates capability level parsing, disabled component resolution,
should_component_run logic, and boundary cases.
"""

import pytest

from lib.capability_levels import (
    DEFAULT_AUTO_DISABLE,
    DEFAULT_LEVEL,
    VALID_LEVELS,
    format_capability_report,
    get_auto_disable_map,
    get_capability_level,
    get_disabled_components,
    should_component_run,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# get_capability_level
# ---------------------------------------------------------------------------


class TestGetCapabilityLevel:
    """Tests for get_capability_level()."""

    def test_reads_level_from_config(self, tmp_path):
        """Should read the level value from a valid config file."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  level: 2\n"
        )
        assert get_capability_level(str(config)) == 2

    def test_default_when_no_config(self, tmp_path):
        """Should return DEFAULT_LEVEL when config file doesn't exist."""
        result = get_capability_level(str(tmp_path / "nonexistent.yaml"))
        assert result == DEFAULT_LEVEL

    def test_default_when_no_model_capability_section(self, tmp_path):
        """Should return DEFAULT_LEVEL when model_capability is missing."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("project:\n  name: test\n")
        assert get_capability_level(str(config)) == DEFAULT_LEVEL

    def test_default_when_level_missing(self, tmp_path):
        """Should return DEFAULT_LEVEL when level key is missing."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  auto_disable:\n"
            "    3: [context-management]\n"
        )
        assert get_capability_level(str(config)) == DEFAULT_LEVEL

    def test_level_1(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 1\n")
        assert get_capability_level(str(config)) == 1

    def test_level_4(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 4\n")
        assert get_capability_level(str(config)) == 4

    def test_invalid_level_returns_default(self, tmp_path):
        """Out of range levels should return DEFAULT_LEVEL."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 5\n")
        assert get_capability_level(str(config)) == DEFAULT_LEVEL

    def test_zero_level_returns_default(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 0\n")
        assert get_capability_level(str(config)) == DEFAULT_LEVEL

    def test_negative_level_returns_default(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: -1\n")
        assert get_capability_level(str(config)) == DEFAULT_LEVEL

    def test_non_numeric_level_returns_default(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: high\n")
        assert get_capability_level(str(config)) == DEFAULT_LEVEL

    def test_level_with_comment(self, tmp_path):
        """Should handle inline comments correctly."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 2  # good capability\n")
        assert get_capability_level(str(config)) == 2


# ---------------------------------------------------------------------------
# get_disabled_components
# ---------------------------------------------------------------------------


class TestGetDisabledComponents:
    """Tests for get_disabled_components()."""

    def test_level_1_nothing_disabled(self, tmp_path):
        """Level 1 should have no components disabled."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 1\n")
        result = get_disabled_components(1, str(config))
        assert result == []

    def test_level_2_nothing_disabled(self, tmp_path):
        """Level 2 should have no components disabled."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 2\n")
        result = get_disabled_components(2, str(config))
        assert result == []

    def test_level_3_disables_context_management(self, tmp_path):
        """Level 3 should disable context-management."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  level: 3\n"
            "  auto_disable:\n"
            "    3: [context-management]\n"
            "    4: [clarification-gate, assumption-tracking]\n"
        )
        result = get_disabled_components(3, str(config))
        assert "context-management" in result
        assert "clarification-gate" not in result

    def test_level_4_cumulative_disable(self, tmp_path):
        """Level 4 should include level 3 disabled components too."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  level: 4\n"
            "  auto_disable:\n"
            "    3: [context-management]\n"
            "    4: [clarification-gate, assumption-tracking]\n"
        )
        result = get_disabled_components(4, str(config))
        assert "context-management" in result
        assert "clarification-gate" in result
        assert "assumption-tracking" in result

    def test_result_is_sorted(self, tmp_path):
        """Disabled components should be returned sorted."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  auto_disable:\n"
            "    3: [z-component, a-component]\n"
        )
        result = get_disabled_components(3, str(config))
        assert result == sorted(result)

    def test_no_duplicates(self, tmp_path):
        """Should not have duplicate entries even if same component in multiple levels."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  auto_disable:\n"
            "    3: [context-management]\n"
            "    4: [context-management, clarification-gate]\n"
        )
        result = get_disabled_components(4, str(config))
        assert len(result) == len(set(result))

    def test_clamps_below_1(self, tmp_path):
        """Level below 1 should be treated as level 1."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 1\n")
        result = get_disabled_components(0, str(config))
        assert result == []

    def test_clamps_above_4(self, tmp_path):
        """Level above 4 should be treated as level 4."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  auto_disable:\n"
            "    3: [context-management]\n"
            "    4: [clarification-gate]\n"
        )
        result = get_disabled_components(99, str(config))
        assert "context-management" in result
        assert "clarification-gate" in result

    def test_default_auto_disable_used_when_not_in_config(self, tmp_path):
        """Should use DEFAULT_AUTO_DISABLE when config doesn't specify auto_disable."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 3\n")
        result = get_disabled_components(3, str(config))
        expected = sorted(DEFAULT_AUTO_DISABLE.get(3, []))
        assert result == expected


# ---------------------------------------------------------------------------
# should_component_run
# ---------------------------------------------------------------------------


class TestShouldComponentRun:
    """Tests for should_component_run()."""

    def test_active_component_at_level_1(self, tmp_path):
        """All components should be active at level 1."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 1\n")
        assert should_component_run("clarification-gate", 1, str(config)) is True
        assert should_component_run("context-management", 1, str(config)) is True

    def test_disabled_component_at_level_3(self, tmp_path):
        """context-management should be disabled at level 3."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  level: 3\n"
            "  auto_disable:\n"
            "    3: [context-management]\n"
        )
        assert should_component_run("context-management", 3, str(config)) is False

    def test_active_component_at_level_3(self, tmp_path):
        """clarification-gate should still be active at level 3."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  level: 3\n"
            "  auto_disable:\n"
            "    3: [context-management]\n"
            "    4: [clarification-gate]\n"
        )
        assert should_component_run("clarification-gate", 3, str(config)) is True

    def test_disabled_at_level_4(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  auto_disable:\n"
            "    4: [blast-radius]\n"
        )
        assert should_component_run("blast-radius", 4, str(config)) is False

    def test_unknown_component_always_runs(self, tmp_path):
        """Components not in any disable list should always run."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  auto_disable:\n"
            "    4: [clarification-gate]\n"
        )
        assert should_component_run("unknown-component", 4, str(config)) is True

    def test_reads_level_from_config_when_none(self, tmp_path):
        """When level is None, should read from config."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  level: 4\n"
            "  auto_disable:\n"
            "    4: [blast-radius]\n"
        )
        assert should_component_run("blast-radius", None, str(config)) is False


# ---------------------------------------------------------------------------
# format_capability_report
# ---------------------------------------------------------------------------


class TestFormatCapabilityReport:
    """Tests for format_capability_report()."""

    def test_report_contains_level(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 3\n")
        report = format_capability_report(3, str(config))
        assert "Level: 3" in report
        assert "excellent" in report

    def test_report_shows_disabled_components(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  auto_disable:\n"
            "    3: [context-management]\n"
        )
        report = format_capability_report(3, str(config))
        assert "context-management" in report
        assert "Disabled components:" in report

    def test_report_level_1_all_active(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 1\n")
        report = format_capability_report(1, str(config))
        assert "All components active" in report

    def test_report_shows_auto_disable_schedule(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  auto_disable:\n"
            "    3: [context-management]\n"
            "    4: [clarification-gate]\n"
        )
        report = format_capability_report(1, str(config))
        assert "Auto-disable schedule:" in report
        assert "Level 3:" in report
        assert "Level 4:" in report

    def test_report_level_4_autonomous(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 4\n")
        report = format_capability_report(4, str(config))
        assert "autonomous" in report


# ---------------------------------------------------------------------------
# get_auto_disable_map
# ---------------------------------------------------------------------------


class TestGetAutoDisableMap:
    """Tests for get_auto_disable_map()."""

    def test_reads_from_config(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  auto_disable:\n"
            "    2: [foo]\n"
            "    3: [bar, baz]\n"
        )
        result = get_auto_disable_map(str(config))
        assert result[2] == ["foo"]
        assert sorted(result[3]) == ["bar", "baz"]

    def test_defaults_when_no_config(self, tmp_path):
        result = get_auto_disable_map(str(tmp_path / "nonexistent.yaml"))
        assert result == DEFAULT_AUTO_DISABLE

    def test_defaults_when_no_auto_disable(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 3\n")
        result = get_auto_disable_map(str(config))
        assert result == DEFAULT_AUTO_DISABLE

    def test_empty_auto_disable_uses_defaults(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "model_capability:\n"
            "  auto_disable: {}\n"
        )
        result = get_auto_disable_map(str(config))
        assert result == DEFAULT_AUTO_DISABLE
