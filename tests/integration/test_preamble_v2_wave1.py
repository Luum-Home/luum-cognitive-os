"""Integration tests for ADR-038 Wave 1 preamble additions.

Verifies that templates/agent-preamble.md contains the three new literals
required by ADR-038 Wave 1:
  1. MAX 20 reasoning cycles (Gap #4)
  2. RETRY DIVERSITY (Gap #7)
  3. MEMORY SCOPE: (Gap #8)

Also includes behavioral tests for retry_tracker and AgentStart backward
compatibility (max_reasoning_cycles default).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.retry_tracker import approach_seen, approaches_tried, record_attempt
from lib.harness_adapter.base import AgentStart

PREAMBLE = Path(__file__).resolve().parents[2] / "templates" / "agent-preamble.md"


@pytest.fixture(scope="module")
def preamble_text():
    assert PREAMBLE.exists(), f"Preamble not found at {PREAMBLE}"
    return PREAMBLE.read_text(encoding="utf-8")


class TestPreambleV2Wave1:
    def test_max_20_reasoning_cycles(self, preamble_text):
        """Preamble must contain 'MAX 20 reasoning' (Gap #4 — iteration cap)."""
        assert "MAX 20 reasoning" in preamble_text, (
            "Expected 'MAX 20 reasoning' in agent-preamble.md. "
            "ADR-038 Gap #4 requires an explicit reasoning-cycle cap."
        )

    def test_retry_diversity_protocol(self, preamble_text):
        """Preamble must contain 'RETRY DIVERSITY' (Gap #7 — retry diversity)."""
        assert "RETRY DIVERSITY" in preamble_text, (
            "Expected 'RETRY DIVERSITY' in agent-preamble.md. "
            "ADR-038 Gap #7 requires per-attempt approach differentiation."
        )

    def test_memory_scope_tiers(self, preamble_text):
        """Preamble must contain 'MEMORY SCOPE:' (Gap #8 — tiered memory access)."""
        assert "MEMORY SCOPE:" in preamble_text, (
            "Expected 'MEMORY SCOPE:' in agent-preamble.md. "
            "ADR-038 Gap #8 requires tiered memory scope declaration."
        )


class TestRetryTrackerBehavior:
    """Behavioral tests verifying retry_tracker logic (not just string presence)."""

    def test_approach_seen_changes_after_record(self, tmp_path):
        """approach_seen returns False before record_attempt, True after."""
        agent_id = "preamble-wave1-integration-agent"
        approach = "use-stdlib-json-parser"

        # Before recording: not seen
        assert approach_seen(agent_id, approach, project_dir=str(tmp_path)) is False

        # Record the attempt
        record_attempt(agent_id, approach, project_dir=str(tmp_path))

        # After recording: seen
        assert approach_seen(agent_id, approach, project_dir=str(tmp_path)) is True

    def test_approaches_tried_count_grows(self, tmp_path):
        """approaches_tried returns a list that grows with each record_attempt call."""
        agent_id = "preamble-wave1-growth-agent"

        assert len(approaches_tried(agent_id, project_dir=str(tmp_path))) == 0

        record_attempt(agent_id, "alpha", project_dir=str(tmp_path))
        assert len(approaches_tried(agent_id, project_dir=str(tmp_path))) == 1

        record_attempt(agent_id, "beta", project_dir=str(tmp_path))
        assert len(approaches_tried(agent_id, project_dir=str(tmp_path))) == 2


class TestAgentStartBackwardCompat:
    """Behavioral test: AgentStart.max_reasoning_cycles default preserves compat."""

    def test_default_value_is_20(self):
        """AgentStart created without max_reasoning_cycles defaults to 20."""
        event = AgentStart(agent_id="compat-agent", started_at=1.0)
        assert event.max_reasoning_cycles == 20

    def test_roundtrip_preserves_custom_value(self):
        """Custom max_reasoning_cycles survives to_dict/from_dict roundtrip."""
        from lib.harness_adapter.base import CanonicalEvent

        original = AgentStart(agent_id="compat-agent", started_at=1.0, max_reasoning_cycles=10)
        data = original.to_dict()
        assert data["max_reasoning_cycles"] == 10

        restored = CanonicalEvent.from_dict(data)
        assert restored.max_reasoning_cycles == 10  # type: ignore[attr-defined]
