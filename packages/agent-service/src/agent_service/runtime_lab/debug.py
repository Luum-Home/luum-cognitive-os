"""Runtime event recording used by sync responses and SSE streams."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class RuntimeEvent:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type,
            "payload": self.payload,
        }


class EventRecorder:
    """In-memory event sink for the runtime lab."""

    def __init__(self) -> None:
        self._events: list[RuntimeEvent] = []

    def record(self, event_type: str, **payload: Any) -> RuntimeEvent:
        event = RuntimeEvent(type=event_type, payload=dict(payload))
        self._events.append(event)
        return event

    @property
    def events(self) -> list[RuntimeEvent]:
        return list(self._events)
