from __future__ import annotations

from lib.event_projections.cost_ledger import fold as cost_fold
from lib.event_projections.handoff_chain import fold as handoff_fold
from lib.event_projections.retry_classifier import fold as retry_fold
from lib.event_projections.timeline import fold as timeline_fold


def test_projection_stubs_fold_minimal_state() -> None:
    event = {"seq": 1, "event_type": "dispatch-error", "ts": "2026-05-07T00:00:00Z", "payload": {"cost_usd": 0.25, "error_code": "ECONNRESET"}}
    assert timeline_fold(None, event)["events"] == [{"seq": 1, "event_type": "dispatch-error", "ts": "2026-05-07T00:00:00Z"}]
    assert cost_fold(None, event)["total_cost_usd"] == 0.25
    assert retry_fold(None, event)["transient_failures"] == 1


def test_handoff_projection_detects_cycle() -> None:
    state = handoff_fold(None, {"seq": 2, "event_type": "handoff-requested", "payload": {"to_agent": "writer", "call_chain": ["researcher", "writer"]}})
    assert state["cycles_detected"] == 1
