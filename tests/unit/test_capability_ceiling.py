"""Tests for read-only capability-ceiling signal detection."""

from lib.capability_ceiling import (
    CapabilitySignal,
    detect_capability_ceiling,
)


def test_detects_explicit_deeper_reasoning_handoff():
    output = """
ESCALATION:
  Type: NEEDS_DEEPER_REASONING
  Capability: reasoning
  Attempted: compared both algorithms and reproduced the failure
  Context_summary: current proof fails on the boundary case
  Partial_result: failing input is n=0
  Recommended_action: upgrade_model
"""

    handoff = detect_capability_ceiling(
        output, original_task="fix parser", source_agent_id="agent-1"
    )

    assert handoff is not None
    assert handoff.signal is CapabilitySignal.NEEDS_DEEPER_REASONING
    assert handoff.capability == "reasoning"
    assert handoff.recommended_action == "upgrade_model"
    assert handoff.context_summary == "current proof fails on the boundary case"
    assert handoff.partial_result == "failing input is n=0"
    assert handoff.original_task == "fix parser"
    assert handoff.source_agent_id == "agent-1"
    assert handoff.auto_redispatch_allowed is False
    assert handoff.to_dict()["signal"] == "NEEDS_DEEPER_REASONING"


def test_detects_tool_access_from_inline_signal_with_defaults():
    handoff = detect_capability_ceiling(
        "I cannot continue: NEEDS_TOOL_ACCESS for browser automation."
    )

    assert handoff is not None
    assert handoff.signal is CapabilitySignal.NEEDS_TOOL_ACCESS
    assert handoff.capability == "tool_access"
    assert handoff.recommended_action == "grant_tool_or_human_review"
    assert handoff.auto_redispatch_allowed is False


def test_ignores_generic_escalation_without_capability_signal():
    output = """
ESCALATION:
  Type: error_repeat
  Evidence: same command failed twice
"""

    assert detect_capability_ceiling(output) is None
