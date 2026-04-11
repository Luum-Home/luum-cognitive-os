"""Behavior tests for agent preamble completeness.

Tests verify that the agent preamble template covers all required sections
that sub-agents need for proper behavior in the Cognitive OS.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).parent.parent.parent
PREAMBLE_PATH = PROJECT_ROOT / "templates" / "agent-preamble.md"


@pytest.fixture
def preamble_content() -> str:
    """Read and return the preamble content."""
    return PREAMBLE_PATH.read_text()


class TestPreambleRequiredSections:
    """Verify the preamble covers all mandatory behavioral sections."""

    def test_has_phase_context(self, preamble_content):
        """Preamble must reference the project phase for phase-aware behavior."""
        assert "phase" in preamble_content.lower(), (
            "Preamble must reference project phase ({{phase}} or 'phase')"
        )

    def test_has_error_handling(self, preamble_content):
        """Preamble must document error handling / retry behavior."""
        lower = preamble_content.lower()
        has_retry = "retry" in lower
        has_error = "error" in lower
        has_escalat = "escalat" in lower
        assert has_retry or has_error or has_escalat, (
            "Preamble must mention retry, error, or escalation handling"
        )

    def test_has_memory_instructions(self, preamble_content):
        """Preamble must instruct agents to save discoveries to engram."""
        lower = preamble_content.lower()
        assert "engram" in lower or "mem_save" in lower, (
            "Preamble must mention engram or mem_save for memory persistence"
        )

    def test_has_clarification_protocol(self, preamble_content):
        """Preamble must document the NEEDS_CLARIFICATION protocol."""
        assert "NEEDS_CLARIFICATION" in preamble_content, (
            "Preamble must mention NEEDS_CLARIFICATION marker"
        )

    def test_has_progress_reporting(self, preamble_content):
        """Preamble must document progress reporting markers."""
        assert "PROGRESS" in preamble_content, (
            "Preamble must mention PROGRESS marker"
        )
        assert "FILES_CREATED" in preamble_content or "FILES_MODIFIED" in preamble_content, (
            "Preamble must mention FILES_CREATED or FILES_MODIFIED markers"
        )

    def test_has_content_policy(self, preamble_content):
        """Preamble must reference content policy enforcement."""
        lower = preamble_content.lower()
        assert "content" in lower and "policy" in lower or "prohibited" in lower, (
            "Preamble must mention content-policy or prohibited terms"
        )

    def test_has_communication_standards(self, preamble_content):
        """Preamble must enforce direct communication (anti-sycophancy)."""
        lower = preamble_content.lower()
        has_flattery = "flattery" in lower
        has_direct = "direct" in lower
        assert has_flattery or has_direct, (
            "Preamble must mention flattery avoidance or direct communication"
        )

    def test_has_background_execution(self, preamble_content):
        """Preamble must document background execution for long commands."""
        assert "run_in_background" in preamble_content, (
            "Preamble must mention run_in_background"
        )
        assert "Long-Running" in preamble_content, (
            "Preamble must have a Long-Running Commands section"
        )


class TestPreambleQuality:
    """Verify the preamble stays within quality bounds."""

    def test_preamble_under_token_budget(self, preamble_content):
        """Preamble should be under 8000 characters to avoid context bloat.

        The preamble is injected into EVERY sub-agent launch. A bloated
        preamble wastes tokens across all delegations. Budget raised from
        6000 to 8000 after adding Context Injection (WS16) and
        Incremental Progress Saves (WS13b) sections.
        TODO(TO-7): Compress preamble back under 6000 via reference-based
        loading instead of inline content.
        """
        char_count = len(preamble_content)
        assert char_count < 8000, (
            f"Preamble is {char_count} chars, should be under 8000 to stay "
            f"within token budget for sub-agent injection"
        )

    def test_no_placeholder_unfilled(self, preamble_content):
        """No literal {{placeholder}} markers should remain unfilled.

        The only allowed placeholder is {{phase}} which the orchestrator
        fills at launch time. All others indicate a template bug.
        """
        # Find all {{...}} placeholders
        placeholders = re.findall(r"\{\{(\w+)\}\}", preamble_content)
        # {{phase}} is the only allowed placeholder
        unexpected = [p for p in placeholders if p != "phase"]
        assert not unexpected, (
            f"Found unfilled placeholders in preamble: {unexpected}. "
            f"Only {{{{phase}}}} is allowed."
        )

    def test_preamble_file_exists(self):
        """The preamble template file must exist."""
        assert PREAMBLE_PATH.exists(), (
            f"templates/agent-preamble.md must exist at {PREAMBLE_PATH}"
        )

    def test_preamble_not_empty(self, preamble_content):
        """The preamble must not be empty."""
        assert len(preamble_content.strip()) > 100, (
            "Preamble must have substantial content (>100 chars)"
        )
