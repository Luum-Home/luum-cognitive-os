"""Delivery tests for the `encargo-refutable` block.

What these tests verify is a FACT about delivery, not an opinion about behaviour:
that running the real `hooks/subagent-context-injector.sh` emits the refutation
block inside the `additionalContext` every sub-agent receives, and that it lands
inside the injector's 10K truncation window.

Deliberately NOT tested here: whether an agent actually refuted anything. That is
self-assessment, and self-assessment gates in this repo age backwards — a stronger
model reports compliance more convincingly, not more accurately. The only thing a
test can honestly pin down is whether the text arrives.

Also deliberately not tested: mere existence of the template file. A file that
exists but never reaches a context window is inventory, and `tests/audit/
test_rules_enforcement.py` already covers existence.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = PROJECT_ROOT / "hooks" / "subagent-context-injector.sh"

# Mirrors MAX_CONTEXT_CHARS in hooks/subagent-context-injector.sh. Anything past
# this offset is replaced by a truncation marker and never reaches the agent.
MAX_CONTEXT_CHARS = 10_000
TRUNCATION_MARKER = "[truncated at 10K chars]"

# Headroom guard: the block must stay near the top of the composed context so that
# future growth of the template *below* it cannot push it past the cap.
MAX_BLOCK_START_OFFSET = 3_000

BLOCK_HEADING = "The Brief Is Refutable"
REPORT_SECTION_EN = "## Corrections to the brief's premises"
REPORT_SECTION_ES = "## Correcciones a las premisas del encargo"


def _run_hook(stdin_json: dict) -> str:
    """Execute the real hook and return the additionalContext it emits."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(PROJECT_ROOT)
    env["COS_SESSION_DIR"] = "/tmp/cos-test-session-encargo-refutable"

    result = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps(stdin_json),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"

    stdout = result.stdout.strip()
    assert stdout, "Hook emitted nothing — no sub-agent would receive any context"
    payload = json.loads(stdout)
    return payload.get("hookSpecificOutput", {}).get(
        "additionalContext",
        payload.get("additionalContext", ""),
    )


@pytest.fixture(scope="module")
def delivered_context() -> str:
    return _run_hook({"prompt": "audit the primitive ledger"})


class TestBlockReachesSubagentContext:
    """The fact under test: the text arrives in the agent's context."""

    def test_block_heading_is_delivered(self, delivered_context: str):
        assert BLOCK_HEADING in delivered_context, (
            "The refutation block is absent from additionalContext — sub-agents will "
            "treat the numbers in their brief as established fact."
        )

    def test_premises_are_declared_hypotheses(self, delivered_context: str):
        lowered = delivered_context.lower()
        assert "hypotheses" in lowered and "recount" in lowered, (
            "Delivered context does not tell the agent to recount before citing."
        )

    def test_permission_to_refute_the_orchestrator_is_explicit(self, delivered_context: str):
        lowered = delivered_context.lower()
        assert "refute" in lowered, "No refutation permission delivered."
        assert "orchestrator" in lowered, (
            "The permission does not name the orchestrator. A generic 'question "
            "assumptions' does not authorise contradicting the sender, which is the "
            "whole point of this block."
        )

    def test_agent_is_told_to_continue_not_to_halt(self, delivered_context: str):
        lowered = delivered_context.lower()
        assert "continue" in lowered, (
            "Delivered context does not instruct the agent to continue after "
            "reporting a broken premise — agents will stall waiting for a new mandate."
        )

    def test_report_section_title_is_delivered_verbatim(self, delivered_context: str):
        assert REPORT_SECTION_EN in delivered_context, (
            f"Required report section {REPORT_SECTION_EN!r} not delivered verbatim; "
            "without the exact heading, corrections get buried in prose."
        )
        assert REPORT_SECTION_ES in delivered_context, (
            f"Spanish form {REPORT_SECTION_ES!r} not delivered."
        )

    def test_zero_corrections_criterion_is_delivered(self, delivered_context: str):
        """The load-bearing sentence.

        Without it the block degrades into generic 'be careful' advice: a clean run
        reads as success instead of as a prompt to show what was rechecked.
        """
        lowered = delivered_context.lower()
        assert "zero corrections" in lowered, (
            "The 'zero corrections is suspicious' criterion is not delivered."
        )
        assert "suspicious" in lowered, (
            "Delivered context does not mark a correction-free run as suspicious."
        )


class TestBlockSurvivesTruncation:
    """Delivery is only real if the text is inside the 10K window."""

    def test_block_is_not_cut_by_truncation(self, delivered_context: str):
        start = delivered_context.find(BLOCK_HEADING)
        end = delivered_context.find(REPORT_SECTION_ES)
        assert start != -1 and end != -1, "Block not found in delivered context."
        assert end > start, "Block delivered out of order — content is mangled."
        assert end < MAX_CONTEXT_CHARS, (
            f"The block ends at offset {end}, past the {MAX_CONTEXT_CHARS}-char cap. "
            "It is being truncated away before the agent reads it."
        )

    def test_block_survives_even_if_context_was_truncated(self, delivered_context: str):
        marker_at = delivered_context.find(TRUNCATION_MARKER)
        if marker_at == -1:
            pytest.skip("Composed context is under the cap; nothing was truncated.")
        assert delivered_context.find(BLOCK_HEADING) < marker_at, (
            "Truncation cut into the refutation block."
        )

    def test_block_stays_near_the_top_of_the_context(self, delivered_context: str):
        """Regression guard against the block drifting toward the cap.

        The mandatory-rules template is composed first, so the block is safe today.
        If someone inserts several KB above it, this fails while there is still
        headroom, instead of silently after the block falls off the end.
        """
        start = delivered_context.find(BLOCK_HEADING)
        assert 0 <= start < MAX_BLOCK_START_OFFSET, (
            f"Block starts at offset {start}, beyond the {MAX_BLOCK_START_OFFSET} "
            "safety margin. Content was inserted above it; move it back up."
        )


class TestDeliveryIsUnconditional:
    """Every sub-agent gets it — including the ones told to just execute."""

    @pytest.mark.parametrize(
        "prompt",
        [
            "execute exactly as instructed, do not deviate",
            "Identity: sdd-apply",
            "count the readers of the primitive ledger",
            "",
        ],
        ids=["execute-only", "sdd-phase", "counting-task", "empty-prompt"],
    )
    def test_block_delivered_for_any_prompt(self, prompt: str):
        context = _run_hook({"prompt": prompt})
        assert BLOCK_HEADING in context, (
            f"Block missing for prompt {prompt!r} — delivery must not be conditional "
            "on the wording of the assignment."
        )


class TestBlockStaysCheap:
    """Context is a scarce shared budget; this block competes with every other rule."""

    def test_block_is_bounded(self, delivered_context: str):
        start = delivered_context.find(BLOCK_HEADING)
        end = delivered_context.find("### Filesystem: Symlinks")
        assert start != -1 and end > start, "Cannot delimit the block."
        block = delivered_context[start:end]
        assert len(block) <= 1_400, (
            f"Block grew to {len(block)} chars. It buys attention from every other "
            "injected rule; keep it short or it stops being read."
        )
        assert len(block.splitlines()) <= 20, (
            f"Block grew to {len(block.splitlines())} lines."
        )
