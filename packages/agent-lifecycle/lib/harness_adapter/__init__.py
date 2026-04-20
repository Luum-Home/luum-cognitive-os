"""Harness-agnostic event capture layer (ADR-033).

Public surface:
    - CanonicalEvent, AgentStart, AgentEnd, ToolUse, TokenUsage, HeartbeatTick
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
    "ToolUse",
    "TokenUsage",
]
