# SCOPE: both
"""Typed handoff envelope for Cognitive OS agent-to-agent delegation.

ADR-230 makes handoffs an executable contract instead of an implicit prompt
convention. This module is deliberately dependency-free: callers can construct,
serialize, validate, and pass envelopes across harnesses without importing a
runtime orchestrator.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, replace
from typing import Any, ClassVar

SCHEMA_VERSION = "handoff-envelope/v1"
ALLOWED_INTENTS = frozenset({"delegate", "handoff", "query"})
ALLOWED_CONTEXT_MODES = frozenset({"full", "summary", "reference", "none"})


class HandoffEnvelopeError(ValueError):
    """Raised when an envelope violates the ADR-230 schema."""


def _require_non_empty_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandoffEnvelopeError(f"{field_name} must be a non-empty string")
    return value.strip()


def _dedupe_text(values: list[str], field_name: str) -> list[str]:
    if not isinstance(values, list):
        raise HandoffEnvelopeError(f"{field_name} must be a list[str]")
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise HandoffEnvelopeError(f"{field_name} must contain only non-empty strings")
        value = item.strip()
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


@dataclass(frozen=True)
class HandoffEnvelope:
    """Schema-versioned handoff envelope required for cross-agent calls."""

    schema_version: str
    handoff_id: str
    parent_event_seq: int
    from_agent: str
    to_agent: str
    intent: str
    context_mode: str
    context_payload: dict[str, Any]
    granted_tools: list[str]
    granted_blast_radius: int
    depth: int
    call_chain: list[str]
    deadline_ts: str | None = None
    return_control: bool = True

    SCHEMA_VERSION: ClassVar[str] = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise HandoffEnvelopeError(f"schema_version must be {SCHEMA_VERSION!r}")
        _require_non_empty_text(self.handoff_id, "handoff_id")
        _require_non_empty_text(self.from_agent, "from_agent")
        _require_non_empty_text(self.to_agent, "to_agent")
        if self.intent not in ALLOWED_INTENTS:
            raise HandoffEnvelopeError(f"intent must be one of {sorted(ALLOWED_INTENTS)}")
        if self.context_mode not in ALLOWED_CONTEXT_MODES:
            raise HandoffEnvelopeError(f"context_mode must be one of {sorted(ALLOWED_CONTEXT_MODES)}")
        if not isinstance(self.parent_event_seq, int) or self.parent_event_seq < 0:
            raise HandoffEnvelopeError("parent_event_seq must be an int >= 0")
        if not isinstance(self.context_payload, dict):
            raise HandoffEnvelopeError("context_payload must be a dict")
        if not isinstance(self.granted_blast_radius, int) or self.granted_blast_radius < 0:
            raise HandoffEnvelopeError("granted_blast_radius must be an int >= 0")
        if not isinstance(self.depth, int) or self.depth < 0:
            raise HandoffEnvelopeError("depth must be an int >= 0")
        if self.deadline_ts is not None and not isinstance(self.deadline_ts, str):
            raise HandoffEnvelopeError("deadline_ts must be a string or None")
        if not isinstance(self.return_control, bool):
            raise HandoffEnvelopeError("return_control must be a bool")
        object.__setattr__(self, "from_agent", self.from_agent.strip())
        object.__setattr__(self, "to_agent", self.to_agent.strip())
        object.__setattr__(self, "handoff_id", self.handoff_id.strip())
        object.__setattr__(self, "granted_tools", _dedupe_text(self.granted_tools, "granted_tools"))
        object.__setattr__(self, "call_chain", _dedupe_text(self.call_chain, "call_chain"))

    @classmethod
    def create(
        cls,
        *,
        parent_event_seq: int,
        from_agent: str,
        to_agent: str,
        intent: str = "delegate",
        context_mode: str = "summary",
        context_payload: dict[str, Any] | None = None,
        granted_tools: list[str] | None = None,
        granted_blast_radius: int = 0,
        depth: int = 0,
        call_chain: list[str] | None = None,
        deadline_ts: str | None = None,
        return_control: bool | None = None,
        handoff_id: str | None = None,
    ) -> "HandoffEnvelope":
        """Create a v1 envelope with a generated id and sane intent defaults."""
        resolved_return_control = intent != "handoff" if return_control is None else return_control
        return cls(
            schema_version=SCHEMA_VERSION,
            handoff_id=handoff_id or str(uuid.uuid4()),
            parent_event_seq=parent_event_seq,
            from_agent=from_agent,
            to_agent=to_agent,
            intent=intent,
            context_mode=context_mode,
            context_payload=context_payload or {},
            granted_tools=granted_tools or [],
            granted_blast_radius=granted_blast_radius,
            depth=depth,
            call_chain=call_chain or [from_agent],
            deadline_ts=deadline_ts,
            return_control=resolved_return_control,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HandoffEnvelope":
        """Load an envelope from JSON-compatible data."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        return asdict(self)

    def with_updates(self, **updates: Any) -> "HandoffEnvelope":
        """Return a validated copy with selected fields updated."""
        return replace(self, **updates)

    def next_hop(self, *, to_agent: str, intent: str | None = None, context_payload: dict[str, Any] | None = None) -> "HandoffEnvelope":
        """Build the next-hop envelope preserving lineage and incrementing depth."""
        return HandoffEnvelope.create(
            parent_event_seq=self.parent_event_seq,
            from_agent=self.to_agent,
            to_agent=to_agent,
            intent=intent or self.intent,
            context_mode=self.context_mode,
            context_payload=self.context_payload if context_payload is None else context_payload,
            granted_tools=list(self.granted_tools),
            granted_blast_radius=self.granted_blast_radius,
            depth=self.depth + 1,
            call_chain=self.call_chain + [self.to_agent],
            deadline_ts=self.deadline_ts,
        )
