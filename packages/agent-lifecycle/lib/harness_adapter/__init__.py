"""Harness-agnostic event capture layer (ADR-033 + ADR-033b).

Public surface:
    - CanonicalEvent, AgentStart, AgentEnd, ToolUse, TokenUsage, HeartbeatTick
    - ParseError (ADR-033b)
    - HarnessName (enum)
    - HarnessAdapter (ABC)

Default dispatch entry point: ``lib.harness_adapter.dispatch.handle_event``.
"""

from .base import (
    AgentEnd,
    AgentStart,
    CanonicalEvent,
    HarnessAdapter,
    HarnessName,
    HeartbeatTick,
    ParseError,
    ToolUse,
    TokenUsage,
)

__all__ = [
    "AgentEnd",
    "AgentStart",
    "CanonicalEvent",
    "HarnessAdapter",
    "HarnessName",
    "HeartbeatTick",
    "ParseError",
    "ToolUse",
    "TokenUsage",
]
