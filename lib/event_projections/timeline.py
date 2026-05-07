from __future__ import annotations

from typing import Any


def fold(state: dict[str, Any] | None, event: dict[str, Any]) -> dict[str, Any]:
    state = dict(state or {"events": []})
    state.setdefault("events", []).append({"seq": event.get("seq"), "event_type": event.get("event_type"), "ts": event.get("ts")})
    return state
