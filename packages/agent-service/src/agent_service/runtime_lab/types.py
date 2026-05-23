"""Provider-agnostic runtime message types.

Do not confuse these LLM-provider types with ``internal/provider`` in the Go
kernel, which adapts host harnesses such as Claude Code and Codex.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class BlockType(StrEnum):
    TEXT = "text"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


@dataclass(frozen=True)
class Block:
    type: BlockType
    text: str = ""
    tool_use_id: str = ""
    tool_name: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)
    tool_result: str = ""
    is_error: bool = False

    @staticmethod
    def text_block(text: str) -> "Block":
        return Block(type=BlockType.TEXT, text=text)

    @staticmethod
    def tool_use(tool_use_id: str, name: str, payload: dict[str, Any]) -> "Block":
        return Block(
            type=BlockType.TOOL_USE,
            tool_use_id=tool_use_id,
            tool_name=name,
            tool_input=dict(payload),
        )

    @staticmethod
    def tool_result_block(tool_use_id: str, result: str, *, is_error: bool) -> "Block":
        return Block(
            type=BlockType.TOOL_RESULT,
            tool_use_id=tool_use_id,
            tool_result=result,
            is_error=is_error,
        )


@dataclass(frozen=True)
class Message:
    role: Role
    content: list[Block]

    def has_tool_result(self) -> bool:
        return any(block.type == BlockType.TOOL_RESULT for block in self.content)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LLMResponse:
    content: list[Block]
    stop_reason: str = "end_turn"
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolExecutionResult:
    content: str
    is_error: bool = False


def render_transcript(messages: list[Message]) -> str:
    lines: list[str] = []
    for message in messages:
        parts: list[str] = []
        for block in message.content:
            if block.type == BlockType.TEXT:
                parts.append(block.text)
            elif block.type == BlockType.TOOL_USE:
                parts.append(f"[called {block.tool_name} with {block.tool_input}]")
            elif block.type == BlockType.TOOL_RESULT:
                parts.append(f"[tool result: {block.tool_result}]")
        lines.append(f"{message.role.value}: " + " ".join(parts))
    return "\n".join(lines)
