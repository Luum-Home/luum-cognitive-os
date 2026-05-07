from __future__ import annotations

from typing import Any


def fold(state: dict[str, Any] | None, event: dict[str, Any]) -> dict[str, Any]:
    state = dict(state or {"handoffs": [], "cycles_detected": 0})
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    if event.get("event_type") == "handoff-requested":
        to_agent = payload.get("to_agent")
        chain = list(payload.get("call_chain") or [])
        state.setdefault("handoffs", []).append({"seq": event.get("seq"), "to_agent": to_agent})
        if to_agent in chain:
            state["cycles_detected"] = int(state.get("cycles_detected", 0)) + 1
    return state
