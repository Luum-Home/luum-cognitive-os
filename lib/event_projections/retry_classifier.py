from __future__ import annotations

from typing import Any

TRANSIENT_CODES = {"ECONNRESET", "EPIPE", "ETIMEDOUT", "429", "rate_limit"}


def fold(state: dict[str, Any] | None, event: dict[str, Any]) -> dict[str, Any]:
    state = dict(state or {"transient_failures": 0, "permanent_failures": 0})
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    code = str(payload.get("error_code") or payload.get("code") or "")
    if event.get("event_type") in {"dispatch-error", "tool-error"}:
        if code in TRANSIENT_CODES:
            state["transient_failures"] = int(state.get("transient_failures", 0)) + 1
        else:
            state["permanent_failures"] = int(state.get("permanent_failures", 0)) + 1
    return state
