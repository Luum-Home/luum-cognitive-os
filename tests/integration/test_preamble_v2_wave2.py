"""Integration tests for the agent preamble context budget.

C4 governance-noop-prune (Pocock-pass, 2026-07-02): the ADR-038 Wave-2/3
agent-facing blocks (INPUT SCHEMA, CONTEXT BUDGET, TRUST-report schema detail)
were injected into every sub-agent before their enforcement was ever wired —
no registered hook consumed them (evidence: engram
sdd/governance-noop-prune/explore). They were pruned as injected-and-hoped
no-ops. These tests now guard the lean state (the sediment must not creep back)
and confirm the load-bearing contract survives.

The real context budget still lives in cognitive-os.yaml and is enforced
hook-side by lib/context_budget.py, independent of any agent-facing prose —
so the TestContextBudgetYaml checks below remain meaningful and unchanged.
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


class TestPreambleLeanAfterC4:
    """Guards the C4 prune: dormant ADR-038 no-op prose must not return, and the
    load-bearing contract the orchestrator actually consumes must stay."""

    def test_dormant_wave2_blocks_not_reinjected(self, preamble_text):
        """The pruned injected-and-hoped blocks must not creep back in."""
        for literal in ("INPUT SCHEMA", "CONTEXT BUDGET", "agent_input_validator"):
            assert literal not in preamble_text, (
                f"'{literal}' reappeared in agent-preamble.md. It was pruned in C4 as an "
                "injected-and-hoped no-op (no registered hook enforces it). If the feature "
                "is wanted, wire the enforcer — do not re-inject unenforced prose."
            )

    def test_load_bearing_result_contract_present(self, preamble_text):
        """The RESULT/TRUST_REPORT contract (consumed out-of-band by the orchestrator) stays."""
        assert "RESULT:" in preamble_text
        assert "TRUST_REPORT: SCORE=" in preamble_text

    def test_auto_trigger_receiver_contract_present(self, preamble_text):
        """AUTO-TRIGGER receiver contract is load-bearing — hooks emit these lines."""
        assert "AUTO-TRIGGER" in preamble_text


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
