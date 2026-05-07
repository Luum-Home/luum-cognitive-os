from __future__ import annotations

import pytest

from lib.handoff_dispatcher import (
    HandoffBlockedByOperator,
    HandoffCycleDetected,
    HandoffDepthExceeded,
    HandoffDispatcher,
)
from lib.handoff_envelope import HandoffEnvelope


def _envelope(**overrides):
    data = dict(parent_event_seq=1, from_agent="a", to_agent="b", call_chain=["a"], granted_tools=["Read", "Write"])
    data.update(overrides)
    return HandoffEnvelope.create(**data)


@pytest.mark.unit
def test_cycle_detection_runs_before_other_side_effects() -> None:
    emitted: list[str] = []
    dispatcher = HandoffDispatcher(event_sink=lambda event_type, payload: emitted.append(event_type) or None)
    envelope = _envelope(to_agent="a", depth=99, granted_blast_radius=999)

    with pytest.raises(HandoffCycleDetected) as exc:
        dispatcher.dispatch(envelope)

    assert exc.value.cycle == ["a", "a"]
    assert emitted == ["handoff.cycle_detected"]


@pytest.mark.unit
def test_depth_exceeded_blocks_before_permission_scope_down() -> None:
    emitted: list[str] = []
    dispatcher = HandoffDispatcher(max_handoff_depth=2, event_sink=lambda event_type, payload: emitted.append(event_type) or None)

    with pytest.raises(HandoffDepthExceeded):
        dispatcher.dispatch(_envelope(depth=3))

    assert emitted == ["handoff.depth_exceeded"]


@pytest.mark.unit
def test_permission_intersection_and_query_read_only() -> None:
    emitted: list[str] = []
    dispatcher = HandoffDispatcher(
        receiver_tools={"b": ["Read"]},
        event_sink=lambda event_type, payload: emitted.append(event_type) or None,
    )

    result = dispatcher.dispatch(_envelope(granted_tools=["Read", "Write", "Bash"]))

    assert result.delivered is True
    assert result.envelope.granted_tools == ["Read"]
    assert "handoff.permission.scoped_down" in emitted

    query = HandoffDispatcher(event_sink=lambda event_type, payload: None).dispatch(
        _envelope(intent="query", granted_tools=["Read"])
    )
    assert query.envelope.granted_tools == []


@pytest.mark.unit
def test_blast_radius_requires_operator_approval() -> None:
    dispatcher = HandoffDispatcher(blast_radius_threshold=1)

    with pytest.raises(HandoffBlockedByOperator):
        dispatcher.dispatch(_envelope(granted_blast_radius=2))

    approved = HandoffDispatcher(blast_radius_threshold=1, operator_approved=True).dispatch(
        _envelope(granted_blast_radius=2)
    )
    assert approved.delivered is True


@pytest.mark.unit
def test_same_handoff_id_is_idempotent(tmp_path) -> None:
    dispatcher = HandoffDispatcher(project_dir=tmp_path, session_id="s1")
    envelope = _envelope(handoff_id="same-id")

    first = dispatcher.dispatch(envelope)
    second = dispatcher.dispatch(envelope)

    assert first.delivered is True
    assert second.delivered is False
    assert second.duplicate is True
