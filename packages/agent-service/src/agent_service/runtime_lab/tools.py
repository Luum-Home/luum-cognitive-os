"""Typed runtime tool registry and built-in lab tools."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Protocol

from agent_service.runtime_lab.approval import ApprovalPolicy, ApprovalRequest
from agent_service.runtime_lab.debug import EventRecorder
from agent_service.runtime_lab.types import ToolDefinition, ToolExecutionResult


class Tool(Protocol):
    def definition(self) -> ToolDefinition:
        """Return provider-facing tool metadata."""

    def execute(
        self,
        payload: dict[str, object],
        approvals: ApprovalPolicy,
        events: EventRecorder,
    ) -> ToolExecutionResult:
        """Run the tool after any required approval policy checks."""


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        self._tools[tool.definition().name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def definitions(self) -> list[ToolDefinition]:
        return [self._tools[name].definition() for name in sorted(self._tools)]

    def execute(
        self,
        name: str,
        payload: dict[str, object],
        approvals: ApprovalPolicy,
        events: EventRecorder,
    ) -> ToolExecutionResult:
        tool = self.get(name)
        if tool is None:
            return ToolExecutionResult(f"unknown tool: {name}", is_error=True)
        events.record("tool.request", name=name, input=payload)
        result = tool.execute(payload, approvals, events)
        events.record(
            "tool.result",
            name=name,
            is_error=result.is_error,
            bytes=len(result.content.encode("utf-8")),
        )
        return result


class EchoTool:
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="echo",
            description="Return the provided text unchanged.",
            input_schema={"text": {"type": "string"}},
            required=["text"],
        )

    def execute(
        self,
        payload: dict[str, object],
        approvals: ApprovalPolicy,
        events: EventRecorder,
    ) -> ToolExecutionResult:
        return ToolExecutionResult(str(payload.get("text", "")))


class WriteFileTool:
    """Write a file only after emitting a unified diff approval request."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_file",
            description="Write content to a workspace-relative file after diff approval.",
            input_schema={
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            required=["path", "content"],
        )

    def execute(
        self,
        payload: dict[str, object],
        approvals: ApprovalPolicy,
        events: EventRecorder,
    ) -> ToolExecutionResult:
        rel_path = str(payload.get("path", ""))
        content = str(payload.get("content", ""))
        if not rel_path:
            return ToolExecutionResult("path is required", is_error=True)
        target = (self.workspace / rel_path).resolve()
        if not _is_relative_to(target, self.workspace):
            return ToolExecutionResult("write_file path escapes workspace", is_error=True)
        before = target.read_text(encoding="utf-8") if target.exists() else ""
        diff = unified_diff(rel_path, before, content, existed=target.exists())
        request = ApprovalRequest(
            tool_name="write_file",
            tool_input={"path": rel_path, "content": content},
            prompt=f"approve write to {rel_path}?",
            diff=diff,
        )
        events.record("tool.approval.request", tool_name="write_file", diff=diff)
        decision = approvals.approve(request)
        events.record(
            "tool.approval.decision",
            tool_name="write_file",
            allowed=decision.allowed,
            reason=decision.reason,
        )
        if not decision.allowed:
            return ToolExecutionResult("user denied this tool call", is_error=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolExecutionResult(f"wrote {len(content)} bytes to {rel_path}")


def unified_diff(path: str, before: str, after: str, *, existed: bool = True) -> str:
    fromfile = f"{path} (current)" if existed else "/dev/null"
    tofile = f"{path} (proposed)"
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
        )
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
