from __future__ import annotations

from typing import Any


def fold(state: dict[str, Any] | None, event: dict[str, Any]) -> dict[str, Any]:
    state = dict(state or {"total_cost_usd": 0.0, "events": 0})
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    cost = payload.get("cost_usd") or payload.get("actual_cost_usd") or 0.0
    try:
        state["total_cost_usd"] = round(float(state.get("total_cost_usd", 0.0)) + float(cost), 8)
    except (TypeError, ValueError):
        pass
    state["events"] = int(state.get("events", 0)) + 1
    return state
