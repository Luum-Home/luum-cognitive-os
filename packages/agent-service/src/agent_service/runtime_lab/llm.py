"""LLM-provider seam for the COS runtime lab."""

from __future__ import annotations

from collections import deque
from typing import Protocol

from agent_service.runtime_lab.debug import EventRecorder
from agent_service.runtime_lab.types import Block, LLMResponse, Message, ToolDefinition


class LLMProvider(Protocol):
    name: str
    model: str

    def send(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        events: EventRecorder,
    ) -> LLMResponse:
        """Send provider-agnostic messages to an LLM backend."""


class MockLLMProvider:
    """Deterministic provider for tests and ADR-291 local sync paths."""

    name = "mock"
    model = "mock-runtime-lab"

    def __init__(self, responses: list[LLMResponse] | None = None) -> None:
        self._responses = deque(responses or [])
        self.calls = 0

    def send(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        events: EventRecorder,
    ) -> LLMResponse:
        self.calls += 1
        events.record(
            "llm.request",
            provider=self.name,
            model=self.model,
            message_count=len(messages),
            tool_names=[tool.name for tool in tools],
        )
        if self._responses:
            response = self._responses.popleft()
        else:
            response = LLMResponse(
                content=[
                    Block.text_block(
                        "local sync query accepted: " + _latest_user_text(messages)
                    )
                ],
                usage={"llm_calls": self.calls},
            )
        events.record(
            "llm.response",
            provider=self.name,
            model=self.model,
            stop_reason=response.stop_reason,
            block_count=len(response.content),
        )
        return response


def _latest_user_text(messages: list[Message]) -> str:
    for message in reversed(messages):
        text = " ".join(block.text for block in message.content if block.text)
        if text:
            return text
    return ""
