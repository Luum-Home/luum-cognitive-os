"""Minimal governed agent loop for ADR-291 runtime lab work."""

from __future__ import annotations

from agent_service.runtime_lab.approval import AlwaysAllowApproval, ApprovalPolicy
from agent_service.runtime_lab.compaction import CompactionStrategy, NoCompaction
from agent_service.runtime_lab.debug import EventRecorder
from agent_service.runtime_lab.llm import LLMProvider
from agent_service.runtime_lab.tools import ToolRegistry
from agent_service.runtime_lab.types import Block, BlockType, Message, Role


class Agent:
    def __init__(
        self,
        provider: LLMProvider,
        tools: ToolRegistry,
        *,
        approvals: ApprovalPolicy | None = None,
        compactor: CompactionStrategy | None = None,
        events: EventRecorder | None = None,
        max_turns: int = 20,
    ) -> None:
        self.provider = provider
        self.tools = tools
        self.approvals = approvals or AlwaysAllowApproval()
        self.compactor = compactor or NoCompaction()
        self.events = events or EventRecorder()
        self.max_turns = max_turns
        self.messages: list[Message] = []

    def send(self, prompt: str) -> str:
        self.messages.append(Message(role=Role.USER, content=[Block.text_block(prompt)]))
        final_text: list[str] = []
        for turn in range(self.max_turns):
            self.events.record("agent.turn.start", turn=turn)
            self.messages = self.compactor.compact(self.messages, self.events)
            response = self.provider.send(
                self.messages,
                self.tools.definitions(),
                self.events,
            )
            self.messages.append(Message(role=Role.ASSISTANT, content=response.content))
            tool_results: list[Block] = []
            has_tool_call = False
            for block in response.content:
                if block.type == BlockType.TEXT and block.text:
                    final_text.append(block.text)
                elif block.type == BlockType.TOOL_USE:
                    has_tool_call = True
                    result = self.tools.execute(
                        block.tool_name,
                        block.tool_input,
                        self.approvals,
                        self.events,
                    )
                    tool_results.append(
                        Block.tool_result_block(
                            block.tool_use_id,
                            result.content,
                            is_error=result.is_error,
                        )
                    )
            if response.stop_reason != "tool_use" or not has_tool_call:
                self.events.record("agent.done", finish_reason=response.stop_reason)
                return "\n".join(final_text).strip()
            self.messages.append(Message(role=Role.USER, content=tool_results))
        self.events.record("agent.error", reason="max_turns_exhausted")
        raise RuntimeError(f"max turns ({self.max_turns}) reached")
