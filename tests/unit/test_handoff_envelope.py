from __future__ import annotations

import pytest

from lib.handoff_envelope import HandoffEnvelope, HandoffEnvelopeError, SCHEMA_VERSION


@pytest.mark.unit
def test_envelope_create_validates_and_defaults_call_chain() -> None:
    envelope = HandoffEnvelope.create(
        parent_event_seq=3,
        from_agent="orchestrator",
        to_agent="worker:1",
        intent="delegate",
        context_mode="reference",
        context_payload={"event_seq_range": [1, 3]},
        granted_tools=["Read", "Read", "Write"],
        granted_blast_radius=2,
    )

    assert envelope.schema_version == SCHEMA_VERSION
    assert envelope.call_chain == ["orchestrator"]
    assert envelope.granted_tools == ["Read", "Write"]
    assert envelope.return_control is True
    assert HandoffEnvelope.from_dict(envelope.to_dict()) == envelope


@pytest.mark.unit
def test_envelope_rejects_invalid_schema_and_intent() -> None:
    with pytest.raises(HandoffEnvelopeError):
        HandoffEnvelope(
            schema_version="wrong/v1",
            handoff_id="h1",
            parent_event_seq=0,
            from_agent="a",
            to_agent="b",
            intent="delegate",
            context_mode="none",
            context_payload={},
            granted_tools=[],
            granted_blast_radius=0,
            depth=0,
            call_chain=["a"],
        )

    with pytest.raises(HandoffEnvelopeError):
        HandoffEnvelope.create(parent_event_seq=0, from_agent="a", to_agent="b", intent="loop")


@pytest.mark.unit
def test_next_hop_preserves_lineage_and_increments_depth() -> None:
    first = HandoffEnvelope.create(parent_event_seq=7, from_agent="a", to_agent="b", call_chain=["a"])
    second = first.next_hop(to_agent="c")

    assert second.from_agent == "b"
    assert second.to_agent == "c"
    assert second.depth == 1
    assert second.call_chain == ["a", "b"]
