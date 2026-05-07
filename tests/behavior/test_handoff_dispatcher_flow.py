from __future__ import annotations

import pytest

from lib.handoff_dispatcher import HandoffCycleDetected, HandoffDispatcher
from lib.handoff_envelope import HandoffEnvelope
from lib.session_bus import read_session_events


@pytest.mark.behavior
def test_round_trip_a_to_b_to_a_records_cycle_only_for_second_hop(tmp_path) -> None:
    dispatcher = HandoffDispatcher(project_dir=tmp_path, session_id="s1")
    first = HandoffEnvelope.create(parent_event_seq=0, from_agent="agent:a", to_agent="agent:b", call_chain=["agent:a"])
    result = dispatcher.dispatch(first)

    assert result.delivered is True

    second = result.envelope.next_hop(to_agent="agent:a")
    with pytest.raises(HandoffCycleDetected):
        dispatcher.dispatch(second)

    events = read_session_events("s1", project_dir=tmp_path)
    assert [event["event_type"] for event in events] == [
        "handoff.requested",
        "handoff.dispatched",
        "handoff.cycle-detected",
    ]
