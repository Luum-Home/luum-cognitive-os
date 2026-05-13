"""Unit tests for lib/sdd_pipeline.py

Validates fast-path activation, phase sequencing, model threshold
comparisons, configuration parsing, and integration with model_catalog.

Author: luum
"""

import pytest

from lib.sdd_pipeline import SDDPipeline, FULL_PHASES, FAST_PHASES, _tier_index

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cfg(enabled: bool = True, threshold: str = "opus") -> dict:
    """Build a minimal config dict with sdd.fast_path settings."""
    return {"sdd": {"fast_path": {"enabled": enabled, "model_threshold": threshold}}}


# ---------------------------------------------------------------------------
# Phase lists
# ---------------------------------------------------------------------------


class TestGetPhases:
    """SDDPipeline.get_phases returns the correct sequence."""

    def test_full_phases_for_sonnet(self) -> None:
        """Sonnet is below the default opus threshold -> full pipeline."""
        phases = SDDPipeline.get_phases("sonnet", _cfg())
        assert phases == list(FULL_PHASES)

    def test_full_phases_for_haiku(self) -> None:
        """Haiku is below the default opus threshold -> full pipeline."""
        phases = SDDPipeline.get_phases("haiku", _cfg())
        assert phases == list(FULL_PHASES)

    def test_fast_phases_for_opus(self) -> None:
        """Opus meets the default opus threshold -> fast path."""
        phases = SDDPipeline.get_phases("opus", _cfg())
        assert phases == list(FAST_PHASES)

    def test_fast_phases_for_opus_canonical(self) -> None:
        """Canonical opus ID also triggers fast path."""
        phases = SDDPipeline.get_phases("claude-opus-4-6", _cfg())
        assert phases == list(FAST_PHASES)

    def test_fast_path_skips_spec_design_tasks(self) -> None:
        """Fast path should not contain spec, design, or tasks."""
        phases = SDDPipeline.get_phases("opus", _cfg())
        assert "spec" not in phases
        assert "design" not in phases
        assert "tasks" not in phases

    def test_fast_path_contains_core_phases(self) -> None:
        """Fast path must still contain explore, propose, apply, verify, archive."""
        phases = SDDPipeline.get_phases("opus", _cfg())
        for p in ("explore", "propose", "apply", "verify", "archive"):
            assert p in phases


# ---------------------------------------------------------------------------
# Config: fast_path disabled
# ---------------------------------------------------------------------------


class TestFastPathDisabled:
    """When fast_path.enabled=false, always use full pipeline."""

    def test_fast_path_disabled_in_config(self) -> None:
        config = _cfg(enabled=False)
        assert SDDPipeline.is_fast_path("opus", config) is False

    def test_disabled_returns_full_phases(self) -> None:
        config = _cfg(enabled=False)
        phases = SDDPipeline.get_phases("opus", config)
        assert phases == list(FULL_PHASES)


# ---------------------------------------------------------------------------
# Custom thresholds
# ---------------------------------------------------------------------------


class TestCustomThreshold:
    """Threshold can be lowered so sonnet+ gets the fast path."""

    def test_sonnet_threshold_allows_sonnet(self) -> None:
        config = _cfg(threshold="sonnet")
        assert SDDPipeline.is_fast_path("sonnet", config) is True

    def test_sonnet_threshold_allows_opus(self) -> None:
        config = _cfg(threshold="sonnet")
        assert SDDPipeline.is_fast_path("opus", config) is True

    def test_sonnet_threshold_blocks_haiku(self) -> None:
        config = _cfg(threshold="sonnet")
        assert SDDPipeline.is_fast_path("haiku", config) is False

    def test_haiku_threshold_allows_all_anthropic(self) -> None:
        config = _cfg(threshold="haiku")
        assert SDDPipeline.is_fast_path("haiku", config) is True
        assert SDDPipeline.is_fast_path("sonnet", config) is True
        assert SDDPipeline.is_fast_path("opus", config) is True


# ---------------------------------------------------------------------------
# next_phase
# ---------------------------------------------------------------------------


class TestNextPhase:
    """SDDPipeline.next_phase advances through the correct sequence."""

    def test_next_phase_full_path(self) -> None:
        config = _cfg(enabled=False)
        assert SDDPipeline.next_phase("explore", "sonnet", config) == "propose"
        assert SDDPipeline.next_phase("propose", "sonnet", config) == "spec"
        assert SDDPipeline.next_phase("spec", "sonnet", config) == "design"
        assert SDDPipeline.next_phase("design", "sonnet", config) == "tasks"
        assert SDDPipeline.next_phase("tasks", "sonnet", config) == "apply"
        assert SDDPipeline.next_phase("apply", "sonnet", config) == "verify"
        assert SDDPipeline.next_phase("verify", "sonnet", config) == "archive"
        assert SDDPipeline.next_phase("archive", "sonnet", config) is None

    def test_next_phase_fast_path(self) -> None:
        config = _cfg()
        assert SDDPipeline.next_phase("explore", "opus", config) == "propose"
        assert SDDPipeline.next_phase("propose", "opus", config) == "apply"
        assert SDDPipeline.next_phase("apply", "opus", config) == "verify"
        assert SDDPipeline.next_phase("verify", "opus", config) == "archive"
        assert SDDPipeline.next_phase("archive", "opus", config) is None

    def test_next_phase_invalid_phase_raises(self) -> None:
        with pytest.raises(ValueError, match="not in the active sequence"):
            SDDPipeline.next_phase("nonexistent", "opus", _cfg())

    def test_next_phase_skipped_phase_raises_in_fast_path(self) -> None:
        """Asking for next after 'spec' in fast path should raise because
        'spec' is not in the fast sequence."""
        with pytest.raises(ValueError, match="not in the active sequence"):
            SDDPipeline.next_phase("spec", "opus", _cfg())


# ---------------------------------------------------------------------------
# skip_reason
# ---------------------------------------------------------------------------


class TestSkipReason:
    """SDDPipeline.skip_reason explains why a phase is skipped."""

    def test_skip_reason_for_skipped_phase(self) -> None:
        reason = SDDPipeline.skip_reason("spec", "opus")
        assert "skipped" in reason.lower()
        assert "opus" in reason
        assert "fast path" in reason.lower()

    def test_skip_reason_for_design(self) -> None:
        reason = SDDPipeline.skip_reason("design", "opus")
        assert reason != ""

    def test_skip_reason_for_tasks(self) -> None:
        reason = SDDPipeline.skip_reason("tasks", "opus")
        assert reason != ""

    def test_skip_reason_empty_for_non_skipped(self) -> None:
        assert SDDPipeline.skip_reason("explore", "opus") == ""
        assert SDDPipeline.skip_reason("propose", "opus") == ""
        assert SDDPipeline.skip_reason("apply", "opus") == ""
        assert SDDPipeline.skip_reason("verify", "opus") == ""
        assert SDDPipeline.skip_reason("archive", "opus") == ""


# ---------------------------------------------------------------------------
# Model catalog integration
# ---------------------------------------------------------------------------


class TestModelCatalogIntegration:
    """Verify that _tier_index resolves aliases via ModelCatalog."""

    def test_canonical_id_resolves(self) -> None:
        assert _tier_index("claude-opus-4-6") == 3

    def test_short_alias_resolves(self) -> None:
        assert _tier_index("opus") == 3
        assert _tier_index("sonnet") == 2
        assert _tier_index("haiku") == 1

    def test_catalog_alias_resolves(self) -> None:
        """Aliases known only in ModelCatalog (not in our local map)
        should still resolve via the fallback."""
        # claude-opus-4-20250514 is only an alias in model_catalog
        from lib.model_catalog import ModelCatalog

        try:
            ModelCatalog.resolve("claude-opus-4-20250514")
            # If the alias exists, _tier_index should resolve it
            assert _tier_index("claude-opus-4-20250514") == 3
        except KeyError:
            pytest.skip("Alias not in current model_catalog")

    def test_unknown_model_returns_negative(self) -> None:
        assert _tier_index("unknown-model-xyz") == -1

    def test_non_anthropic_model_not_fast_path(self) -> None:
        """Non-Anthropic models (gpt-4o, gemini) should not get fast path."""
        config = _cfg(threshold="sonnet")
        assert SDDPipeline.is_fast_path("gpt-4o", config) is False


# ---------------------------------------------------------------------------
# Default config (no config dict passed)
# ---------------------------------------------------------------------------


class TestDefaultConfig:
    """When config=None and no yaml file found, defaults should apply."""

    def test_default_enabled_true(self) -> None:
        """With no config, fast_path defaults to enabled=True, threshold=opus."""
        # When no config file exists, _read_sdd_config returns {},
        # and is_fast_path treats enabled default as True, threshold as opus.
        assert SDDPipeline.is_fast_path("opus") is True

    def test_default_blocks_sonnet(self) -> None:
        assert SDDPipeline.is_fast_path("sonnet") is False


# ---------------------------------------------------------------------------
# Phase constants
# ---------------------------------------------------------------------------


class TestPhaseConstants:
    """Ensure the phase constants are well-formed."""

    def test_full_phases_length(self) -> None:
        assert len(FULL_PHASES) == 8

    def test_fast_phases_length(self) -> None:
        assert len(FAST_PHASES) == 5

    def test_fast_is_subset_of_full(self) -> None:
        assert set(FAST_PHASES).issubset(set(FULL_PHASES))

    def test_full_starts_with_explore(self) -> None:
        assert FULL_PHASES[0] == "explore"

    def test_full_ends_with_archive(self) -> None:
        assert FULL_PHASES[-1] == "archive"

    def test_fast_starts_with_explore(self) -> None:
        assert FAST_PHASES[0] == "explore"

    def test_fast_ends_with_archive(self) -> None:
        assert FAST_PHASES[-1] == "archive"
