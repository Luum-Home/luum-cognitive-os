"""Unit tests for lib/model_catalog.py

Validates alias resolution, upgrade/downgrade chains, provider filtering,
capability queries, cost estimation, pricing consistency with existing
modules, and coverage of all hardcoded model references across lib/*.py.

Author: luum
"""

import re
from pathlib import Path

import pytest

from lib.model_catalog import ModelCatalog, ModelEntry, _ENTRIES

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Alias resolution
# ---------------------------------------------------------------------------


class TestResolveAliases:
    """Every documented alias must resolve to its canonical model ID."""

    def test_opus_aliases(self) -> None:
        assert ModelCatalog.resolve("opus") == "claude-opus-4-6"
        assert ModelCatalog.resolve("claude-opus-4") == "claude-opus-4-6"
        assert ModelCatalog.resolve("claude-opus") == "claude-opus-4-6"
        assert ModelCatalog.resolve("claude-opus-4-6") == "claude-opus-4-6"

    def test_sonnet_aliases(self) -> None:
        assert ModelCatalog.resolve("sonnet") == "claude-sonnet-4"
        assert ModelCatalog.resolve("claude-sonnet") == "claude-sonnet-4"
        assert ModelCatalog.resolve("claude-sonnet-4") == "claude-sonnet-4"

    def test_haiku_aliases(self) -> None:
        assert ModelCatalog.resolve("haiku") == "claude-haiku-3.5"
        assert ModelCatalog.resolve("claude-haiku-3-5") == "claude-haiku-3.5"
        assert ModelCatalog.resolve("claude-haiku") == "claude-haiku-3.5"
        assert ModelCatalog.resolve("claude-haiku-3.5") == "claude-haiku-3.5"

    def test_openrouter_aliases(self) -> None:
        assert ModelCatalog.resolve("openrouter/free") == "openrouter/free"
        assert ModelCatalog.resolve("free") == "openrouter/free"
        assert ModelCatalog.resolve("openrouter-free") == "openrouter/free"

    def test_gpt4o_aliases(self) -> None:
        assert ModelCatalog.resolve("gpt-4o") == "gpt-4o"
        assert ModelCatalog.resolve("gpt4o") == "gpt-4o"

    def test_gemini_aliases(self) -> None:
        assert ModelCatalog.resolve("gemini-2.5-pro") == "gemini-2.5-pro"
        assert ModelCatalog.resolve("gemini-pro") == "gemini-2.5-pro"
        assert ModelCatalog.resolve("gemini") == "gemini-2.5-pro"

    def test_deepseek_alias(self) -> None:
        assert ModelCatalog.resolve("deepseek-r1") == "deepseek-r1"
        assert ModelCatalog.resolve("deepseek") == "deepseek-r1"

    def test_local_model_aliases(self) -> None:
        assert ModelCatalog.resolve("llama-3-70b") == "llama-3-70b"
        assert ModelCatalog.resolve("llama-70b") == "llama-3-70b"
        assert ModelCatalog.resolve("qwen-3-32b") == "qwen-3-32b"
        assert ModelCatalog.resolve("qwen-32b") == "qwen-3-32b"

    def test_case_insensitive(self) -> None:
        assert ModelCatalog.resolve("OPUS") == "claude-opus-4-6"
        assert ModelCatalog.resolve("Sonnet") == "claude-sonnet-4"
        assert ModelCatalog.resolve("HAIKU") == "claude-haiku-3.5"

    def test_unknown_alias_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown model"):
            ModelCatalog.resolve("nonexistent-model")

    def test_all_entries_resolvable_by_id(self) -> None:
        """Every entry's canonical ID must resolve to itself."""
        for entry in _ENTRIES:
            assert ModelCatalog.resolve(entry.id) == entry.id

    def test_all_aliases_resolvable(self) -> None:
        """Every alias declared in every entry must resolve correctly."""
        for entry in _ENTRIES:
            for alias in entry.aliases:
                resolved = ModelCatalog.resolve(alias)
                assert resolved == entry.id, (
                    f"Alias {alias!r} resolved to {resolved!r}, "
                    f"expected {entry.id!r}"
                )


# ---------------------------------------------------------------------------
# Upgrade / downgrade chains
# ---------------------------------------------------------------------------


class TestUpgradeChain:
    """Verify the model upgrade chain: haiku -> sonnet -> opus -> None."""

    def test_haiku_upgrades_to_sonnet(self) -> None:
        assert ModelCatalog.upgrade("claude-haiku-3.5") == "claude-sonnet-4"

    def test_sonnet_upgrades_to_opus(self) -> None:
        assert ModelCatalog.upgrade("claude-sonnet-4") == "claude-opus-4-6"

    def test_opus_has_no_upgrade(self) -> None:
        assert ModelCatalog.upgrade("claude-opus-4-6") is None

    def test_upgrade_via_short_alias(self) -> None:
        assert ModelCatalog.upgrade("haiku") == "claude-sonnet-4"
        assert ModelCatalog.upgrade("sonnet") == "claude-opus-4-6"

    def test_openrouter_free_upgrades_to_haiku(self) -> None:
        assert ModelCatalog.upgrade("openrouter/free") == "claude-haiku-3.5"

    def test_non_chain_model_returns_none(self) -> None:
        assert ModelCatalog.upgrade("gpt-4o") is None


class TestDowngradeChain:
    """Verify the model downgrade chain: opus -> sonnet -> haiku -> free."""

    def test_opus_downgrades_to_sonnet(self) -> None:
        assert ModelCatalog.downgrade("claude-opus-4-6") == "claude-sonnet-4"

    def test_sonnet_downgrades_to_haiku(self) -> None:
        assert ModelCatalog.downgrade("claude-sonnet-4") == "claude-haiku-3.5"

    def test_haiku_downgrades_to_free(self) -> None:
        assert ModelCatalog.downgrade("claude-haiku-3.5") == "openrouter/free"

    def test_free_has_no_downgrade(self) -> None:
        assert ModelCatalog.downgrade("openrouter/free") is None

    def test_downgrade_via_short_alias(self) -> None:
        assert ModelCatalog.downgrade("opus") == "claude-sonnet-4"
        assert ModelCatalog.downgrade("sonnet") == "claude-haiku-3.5"

    def test_non_chain_model_returns_none(self) -> None:
        assert ModelCatalog.downgrade("gpt-4o") is None


# ---------------------------------------------------------------------------
# Provider filtering
# ---------------------------------------------------------------------------


class TestByProvider:
    def test_anthropic_models(self) -> None:
        models = ModelCatalog.by_provider("anthropic")
        ids = {m.id for m in models}
        assert "claude-opus-4-6" in ids
        assert "claude-sonnet-4" in ids
        assert "claude-haiku-3.5" in ids

    def test_openai_models(self) -> None:
        models = ModelCatalog.by_provider("openai")
        ids = {m.id for m in models}
        assert "gpt-4o" in ids

    def test_ollama_local_models(self) -> None:
        models = ModelCatalog.by_provider("ollama")
        assert all(m.local for m in models)
        ids = {m.id for m in models}
        assert "llama-3-70b" in ids
        assert "qwen-3-32b" in ids

    def test_case_insensitive(self) -> None:
        assert len(ModelCatalog.by_provider("Anthropic")) == len(
            ModelCatalog.by_provider("anthropic")
        )

    def test_unknown_provider_returns_empty(self) -> None:
        assert ModelCatalog.by_provider("nonexistent") == []


# ---------------------------------------------------------------------------
# Capability queries
# ---------------------------------------------------------------------------


class TestByCapability:
    def test_reasoning_high(self) -> None:
        models = ModelCatalog.by_capability("reasoning", min_score=8)
        ids = {m.id for m in models}
        assert "claude-opus-4-6" in ids
        assert "gemini-2.5-pro" in ids
        assert "deepseek-r1" in ids

    def test_speed_high(self) -> None:
        models = ModelCatalog.by_capability("speed", min_score=8)
        ids = {m.id for m in models}
        assert "claude-haiku-3.5" in ids

    def test_code_minimum(self) -> None:
        models = ModelCatalog.by_capability("code", min_score=7)
        ids = {m.id for m in models}
        assert "claude-sonnet-4" in ids
        assert "gpt-4o" in ids


class TestCheapestFor:
    def test_cheapest_for_code(self) -> None:
        entry = ModelCatalog.cheapest_for("code", min_score=6)
        # Must be a free or very cheap model with code >= 6
        assert entry.capabilities.get("code", 0) >= 6
        # There should be no cheaper model meeting the same criteria
        candidates = ModelCatalog.by_capability("code", min_score=6)
        cheapest_cost = min(
            c.input_price_per_m + c.output_price_per_m for c in candidates
        )
        assert (
            entry.input_price_per_m + entry.output_price_per_m == cheapest_cost
        )

    def test_cheapest_for_reasoning(self) -> None:
        entry = ModelCatalog.cheapest_for("reasoning", min_score=8)
        assert entry.capabilities.get("reasoning", 0) >= 8

    def test_no_model_meets_criteria_raises(self) -> None:
        with pytest.raises(ValueError, match="No model has"):
            ModelCatalog.cheapest_for("reasoning", min_score=99)


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


class TestEstimateCost:
    def test_opus_cost(self) -> None:
        # 10K input, 5K output
        cost = ModelCatalog.estimate_cost("claude-opus-4-6", 10_000, 5_000)
        expected = 10_000 * 15.0 / 1_000_000 + 5_000 * 75.0 / 1_000_000
        assert cost == pytest.approx(expected, abs=1e-6)

    def test_sonnet_cost(self) -> None:
        cost = ModelCatalog.estimate_cost("sonnet", 10_000, 5_000)
        expected = 10_000 * 3.0 / 1_000_000 + 5_000 * 15.0 / 1_000_000
        assert cost == pytest.approx(expected, abs=1e-6)

    def test_free_model_zero_cost(self) -> None:
        cost = ModelCatalog.estimate_cost("openrouter/free", 100_000, 50_000)
        assert cost == 0.0

    def test_cost_via_alias(self) -> None:
        cost_alias = ModelCatalog.estimate_cost("opus", 10_000, 5_000)
        cost_canonical = ModelCatalog.estimate_cost(
            "claude-opus-4-6", 10_000, 5_000
        )
        assert cost_alias == cost_canonical

    def test_unknown_model_raises(self) -> None:
        with pytest.raises(KeyError):
            ModelCatalog.estimate_cost("nonexistent", 1000, 1000)


# ---------------------------------------------------------------------------
# Pricing consistency with existing modules
# ---------------------------------------------------------------------------


class TestPricingMatchesExisting:
    """Verify that catalog prices match cost_dashboard.MODEL_PRICES and
    model_router.MODEL_CAPABILITIES exactly.
    """

    def test_matches_cost_dashboard(self) -> None:
        from lib.cost_dashboard import MODEL_PRICES

        for name, prices in MODEL_PRICES.items():
            try:
                entry = ModelCatalog.get(name)
            except KeyError:
                pytest.fail(
                    f"cost_dashboard.MODEL_PRICES has model {name!r} "
                    f"which is missing from ModelCatalog"
                )
            assert entry.input_price_per_m == prices["input"], (
                f"Input price mismatch for {name}: catalog={entry.input_price_per_m}, "
                f"dashboard={prices['input']}"
            )
            assert entry.output_price_per_m == prices["output"], (
                f"Output price mismatch for {name}: catalog={entry.output_price_per_m}, "
                f"dashboard={prices['output']}"
            )

    def test_matches_model_router(self) -> None:
        from lib.model_router import MODEL_CAPABILITIES

        for model_id, caps in MODEL_CAPABILITIES.items():
            try:
                entry = ModelCatalog.get(model_id)
            except KeyError:
                pytest.fail(
                    f"model_router.MODEL_CAPABILITIES has model {model_id!r} "
                    f"which is missing from ModelCatalog"
                )
            assert entry.input_price_per_m == caps["cost_per_1m_in"], (
                f"Input price mismatch for {model_id}"
            )
            assert entry.output_price_per_m == caps["cost_per_1m_out"], (
                f"Output price mismatch for {model_id}"
            )
            assert entry.context_window == caps["context"], (
                f"Context window mismatch for {model_id}"
            )

    # NOTE: test_matches_workload_scheduler was deleted on 2026-04-21.
    # lib.workload_scheduler was removed from the codebase (phantom module).
    # The test's intent (verify MODEL_COSTS prices match ModelCatalog) is
    # no longer applicable. See Engram: bugfix/tests/workload-scheduler-phantom


# ---------------------------------------------------------------------------
# All hardcoded model IDs in lib/*.py are present in the catalog
# ---------------------------------------------------------------------------


class TestAllHardcodedModelsInCatalog:
    """Scan lib/*.py for hardcoded model identifiers and verify they all
    exist in the catalog.  This catches drift when new models are added
    to individual modules but not to the catalog.
    """

    # Patterns that look like model IDs in Python source.
    _MODEL_ID_PATTERN = re.compile(
        r"""(?:"|')"""                          # opening quote
        r"""(claude-[a-z0-9.-]+"""              # claude-*
        r"""|gpt-4o"""                          # gpt-4o
        r"""|gemini-[\d.]+-pro"""               # gemini-*-pro
        r"""|deepseek-r1"""                     # deepseek-r1
        r"""|llama-3-70b"""                     # llama-3-70b
        r"""|qwen-3-32b"""                      # qwen-3-32b
        r"""|openrouter/free"""                 # openrouter/free
        r"""|qwen/qwen3-32b:free"""             # qwen/qwen3-32b:free
        r"""|nvidia/llama-3\.1-nemotron[^"']*"""  # nvidia/llama-...:free
        r""")"""
        r"""(?:"|')""",                         # closing quote
    )

    def test_all_lib_model_ids_in_catalog(self) -> None:
        lib_dir = Path(__file__).resolve().parent.parent.parent / "lib"
        assert lib_dir.is_dir(), f"lib directory not found at {lib_dir}"

        missing: list[str] = []
        all_aliases = ModelCatalog.all_aliases()

        for py_file in sorted(lib_dir.glob("*.py")):
            if py_file.name == "model_catalog.py":
                continue  # skip the catalog itself
            text = py_file.read_text(encoding="utf-8")
            for match in self._MODEL_ID_PATTERN.finditer(text):
                model_id = match.group(1)
                if model_id.lower() not in all_aliases:
                    missing.append(f"{py_file.name}: {model_id}")

        if missing:
            pytest.fail(
                "The following model IDs found in lib/*.py are NOT in "
                "ModelCatalog:\n  " + "\n  ".join(missing)
            )


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


class TestFormatCatalog:
    def test_returns_nonempty_string(self) -> None:
        output = ModelCatalog.format_catalog()
        assert isinstance(output, str)
        assert len(output) > 100

    def test_contains_all_canonical_ids(self) -> None:
        output = ModelCatalog.format_catalog()
        for entry in _ENTRIES:
            assert entry.id in output


class TestFamily:
    def test_family_via_alias(self) -> None:
        assert ModelCatalog.family("opus") == "opus"
        assert ModelCatalog.family("sonnet") == "sonnet"
        assert ModelCatalog.family("haiku") == "haiku"
        assert ModelCatalog.family("gpt-4o") == "gpt4"

    def test_family_via_canonical(self) -> None:
        assert ModelCatalog.family("claude-opus-4-6") == "opus"


class TestGetReturnsModelEntry:
    def test_get_returns_entry(self) -> None:
        entry = ModelCatalog.get("opus")
        assert isinstance(entry, ModelEntry)
        assert entry.id == "claude-opus-4-6"

    def test_entry_is_frozen(self) -> None:
        entry = ModelCatalog.get("opus")
        with pytest.raises(AttributeError):
            entry.id = "hacked"  # type: ignore[misc]


class TestPricing:
    def test_pricing_tuple(self) -> None:
        inp, out = ModelCatalog.pricing("claude-opus-4-6")
        assert inp == 15.0
        assert out == 75.0

    def test_pricing_via_alias(self) -> None:
        inp, out = ModelCatalog.pricing("haiku")
        assert inp == 0.25
        assert out == 1.25
