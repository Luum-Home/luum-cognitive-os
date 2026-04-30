"""Integration tests for ADR-038 Wave 2 preamble additions.

Verifies that templates/agent-preamble.md contains the two new literals
required by ADR-038 Wave 2:
  1. INPUT SCHEMA: (Gap #1 — typed input variable contract)
  2. CONTEXT BUDGET: (Gap #2 — 4-layer context budget, Google ADK pattern)

Also verifies that cognitive-os.yaml declares the four context_budget keys
with valid integer values.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PREAMBLE = REPO_ROOT / "templates" / "agent-preamble.md"
COGOS_YAML = REPO_ROOT / "cognitive-os.yaml"


@pytest.fixture(scope="module")
def preamble_text():
    assert PREAMBLE.exists(), f"Preamble not found at {PREAMBLE}"
    return PREAMBLE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def cogos_config():
    assert COGOS_YAML.exists(), f"cognitive-os.yaml not found at {COGOS_YAML}"
    with COGOS_YAML.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class TestPreambleV2Wave2:
    def test_input_schema_literal_present(self, preamble_text):
        """Preamble must contain 'INPUT SCHEMA' (Gap #1 — typed input contract)."""
        assert "INPUT SCHEMA" in preamble_text, (
            "Expected 'INPUT SCHEMA' in agent-preamble.md. "
            "ADR-038 Gap #1 requires a machine-readable field schema block."
        )

    def test_input_schema_has_task_description_field(self, preamble_text):
        """Preamble INPUT SCHEMA must document the canonical task_description field."""
        assert "task_description" in preamble_text, (
            "Expected 'task_description' in agent-preamble.md INPUT SCHEMA block. "
            "This is the canonical required field for all sub-agent launches."
        )

    def test_input_schema_has_required_marker(self, preamble_text):
        """Preamble INPUT SCHEMA must use 'required' markers for mandatory fields."""
        assert "required" in preamble_text, (
            "Expected 'required' marker in agent-preamble.md INPUT SCHEMA block. "
            "Required fields must be distinguished from optional ones."
        )

    def test_context_budget_literal_present(self, preamble_text):
        """Preamble must contain 'CONTEXT BUDGET' (Gap #2 — 4-layer budget)."""
        assert "CONTEXT BUDGET" in preamble_text, (
            "Expected 'CONTEXT BUDGET' in agent-preamble.md. "
            "ADR-038 Gap #2 requires a 4-layer context budget block (Google ADK pattern)."
        )


class TestContextBudgetYaml:
    def test_context_budget_key_exists(self, cogos_config):
        """cognitive-os.yaml must have a top-level 'context_budget' key."""
        assert "context_budget" in cogos_config, (
            "Expected 'context_budget' in cognitive-os.yaml. "
            "ADR-038 Wave 2 requires the 4-layer budget to be declared in config."
        )

    def test_static_max_tokens_is_valid_int(self, cogos_config):
        """context_budget.static_max_tokens must be a positive integer."""
        budget = cogos_config["context_budget"]
        assert isinstance(budget.get("static_max_tokens"), int), (
            "context_budget.static_max_tokens must be an integer."
        )
        assert budget["static_max_tokens"] > 0

    def test_turn_max_tokens_is_valid_int(self, cogos_config):
        """context_budget.turn_max_tokens must be a positive integer."""
        budget = cogos_config["context_budget"]
        assert isinstance(budget.get("turn_max_tokens"), int), (
            "context_budget.turn_max_tokens must be an integer."
        )
        assert budget["turn_max_tokens"] > 0

    def test_user_max_tokens_is_valid_int(self, cogos_config):
        """context_budget.user_max_tokens must be a positive integer."""
        budget = cogos_config["context_budget"]
        assert isinstance(budget.get("user_max_tokens"), int), (
            "context_budget.user_max_tokens must be an integer."
        )
        assert budget["user_max_tokens"] > 0

    def test_cache_max_tokens_is_valid_int(self, cogos_config):
        """context_budget.cache_max_tokens must be a positive integer."""
        budget = cogos_config["context_budget"]
        assert isinstance(budget.get("cache_max_tokens"), int), (
            "context_budget.cache_max_tokens must be an integer."
        )
        assert budget["cache_max_tokens"] > 0

    def test_budget_layer_ordering(self, cogos_config):
        """Context budget layers must be strictly increasing: static < turn < user < cache."""
        b = cogos_config["context_budget"]
        assert b["static_max_tokens"] < b["turn_max_tokens"] < b["user_max_tokens"] < b["cache_max_tokens"], (
            "Budget layers must be ordered: static < turn < user < cache. "
            "This mirrors the Google ADK layered context model."
        )
