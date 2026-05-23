"""Context compaction strategies for the runtime lab."""

from __future__ import annotations

from typing import Protocol

from agent_service.runtime_lab.debug import EventRecorder
from agent_service.runtime_lab.types import Message, Role


class CompactionStrategy(Protocol):
    def compact(self, messages: list[Message], events: EventRecorder) -> list[Message]:
        """Return a safe replacement message list."""


def safe_split_point(messages: list[Message], desired: int) -> int:
    """Find a split that never separates tool_use from its tool_result.

    The boundary is just before a user message that is not carrying tool
    results. Returning 0 means the caller should leave the transcript intact.
    """

    if desired <= 0:
        return 0
    if desired >= len(messages):
        return len(messages)
    for index in range(desired, 0, -1):
        candidate = messages[index]
        if candidate.role == Role.USER and not candidate.has_tool_result():
            return index
    return 0


class NoCompaction:
    def compact(self, messages: list[Message], events: EventRecorder) -> list[Message]:
        return messages


class SafeSlidingWindow:
    def __init__(self, keep_last: int) -> None:
        if keep_last < 1:
            raise ValueError("keep_last must be positive")
        self.keep_last = keep_last

    def compact(self, messages: list[Message], events: EventRecorder) -> list[Message]:
        if len(messages) <= self.keep_last:
            return messages
        split = safe_split_point(messages, len(messages) - self.keep_last)
        if split == 0:
            return messages
        compacted = messages[split:]
        events.record(
            "runtime.compaction",
            strategy="safe_sliding_window",
            before=len(messages),
            after=len(compacted),
        )
        return compacted
