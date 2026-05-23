"""Runtime-lab tests for BYO Harness-inspired ADR-291 seams."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_service.runtime_lab import (
    Agent,
    Block,
    DenyAllApproval,
    EchoTool,
    EventRecorder,
    Message,
    MockLLMProvider,
    Role,
    SafeSlidingWindow,
    ToolRegistry,
    WriteFileTool,
    safe_split_point,
)
from agent_service.runtime_lab.mcp import MCPToolWrapper
from agent_service.runtime_lab.subagents import SubagentTool
from agent_service.runtime_lab.types import LLMResponse, ToolExecutionResult


def test_agent_loop_executes_tool_and_returns_final_text():
    provider = MockLLMProvider(
        [
            LLMResponse(
                content=[Block.tool_use("call-1", "echo", {"text": "hello tool"})],
                stop_reason="tool_use",
            ),
            LLMResponse(content=[Block.text_block("done")]),
        ]
    )
    events = EventRecorder()
    agent = Agent(provider, ToolRegistry([EchoTool()]), events=events)

    assert agent.send("use echo") == "done"
    assert provider.calls == 2
    assert any(event.type == "tool.request" for event in events.events)
    assert agent.messages[-1].role == Role.ASSISTANT


def test_write_file_requires_diff_first_approval(tmp_path: Path):
    existing = tmp_path / "hello.txt"
    existing.write_text("old\n", encoding="utf-8")
    events = EventRecorder()
    tool = WriteFileTool(tmp_path)

    result = tool.execute(
        {"path": "hello.txt", "content": "new\n"},
        DenyAllApproval(),
        events,
    )

    assert result.is_error is True
    assert existing.read_text(encoding="utf-8") == "old\n"
    approval = [event for event in events.events if event.type == "tool.approval.request"][0]
    assert "--- hello.txt (current)" in approval.payload["diff"]
    assert "+++ hello.txt (proposed)" in approval.payload["diff"]
    assert "+new" in approval.payload["diff"]


def test_safe_split_point_does_not_cut_tool_result_pair():
    messages = [
        Message(Role.USER, [Block.text_block("start")]),
        Message(Role.ASSISTANT, [Block.tool_use("1", "echo", {"text": "x"})]),
        Message(Role.USER, [Block.tool_result_block("1", "x", is_error=False)]),
        Message(Role.USER, [Block.text_block("next")]),
        Message(Role.ASSISTANT, [Block.text_block("answer")]),
    ]

    assert safe_split_point(messages, 2) == 0
    assert safe_split_point(messages, 3) == 3
    compacted = SafeSlidingWindow(keep_last=2).compact(messages, EventRecorder())
    assert compacted[0].content[0].text == "next"


def test_subagent_is_exposed_as_governed_tool():
    def factory(events: EventRecorder) -> Agent:
        return Agent(MockLLMProvider(), ToolRegistry([EchoTool()]), events=events)

    registry = ToolRegistry(
        [SubagentTool("research", "Run focused read-only research.", factory)]
    )
    events = EventRecorder()

    result = registry.execute(
        "delegate_research",
        {"task": "inspect x"},
        DenyAllApproval(),
        events,
    )

    assert result.is_error is False
    assert "inspect x" in result.content
    assert [event.type for event in events.events if event.type.startswith("subagent.")] == [
        "subagent.start",
        "subagent.done",
    ]


class FakeMCPClient:
    def call_tool(self, name: str, arguments: dict[str, object]) -> ToolExecutionResult:
        return ToolExecutionResult(f"{name}:{arguments['query']}")


def test_mcp_wrapper_registers_remote_tool_without_replacing_host_mcp():
    wrapper = MCPToolWrapper(
        "docs",
        "search",
        "Search docs",
        {"query": {"type": "string"}},
        ["query"],
        FakeMCPClient(),
    )
    registry = ToolRegistry([wrapper])
    events = EventRecorder()

    assert registry.definitions()[0].name == "docs_search"
    result = registry.execute(
        "docs_search",
        {"query": "memory"},
        DenyAllApproval(),
        events,
    )
    assert result.content == "search:memory"
    assert any(event.type == "mcp.tool.request" for event in events.events)


def test_max_turn_exhaustion_is_explicit():
    provider = MockLLMProvider(
        [
            LLMResponse(
                content=[Block.tool_use("call-1", "echo", {"text": "again"})],
                stop_reason="tool_use",
            ),
            LLMResponse(
                content=[Block.tool_use("call-2", "echo", {"text": "again"})],
                stop_reason="tool_use",
            ),
        ]
    )
    agent = Agent(provider, ToolRegistry([EchoTool()]), max_turns=1)

    with pytest.raises(RuntimeError, match="max turns"):
        agent.send("loop")
