"""Subagent-as-governed-tool support for the runtime lab."""

from __future__ import annotations

from collections.abc import Callable

from agent_service.runtime_lab.agent import Agent
from agent_service.runtime_lab.approval import ApprovalPolicy
from agent_service.runtime_lab.debug import EventRecorder
from agent_service.runtime_lab.types import ToolDefinition, ToolExecutionResult


class SubagentTool:
    def __init__(
        self,
        name: str,
        description: str,
        agent_factory: Callable[[EventRecorder], Agent],
    ) -> None:
        self.name = name
        self.description = description
        self.agent_factory = agent_factory

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=f"delegate_{self.name}",
            description=self.description,
            input_schema={"task": {"type": "string"}},
            required=["task"],
        )

    def execute(
        self,
        payload: dict[str, object],
        approvals: ApprovalPolicy,
        events: EventRecorder,
    ) -> ToolExecutionResult:
        task = str(payload.get("task", ""))
        events.record("subagent.start", name=self.name, task=task)
        agent = self.agent_factory(events)
        try:
            result = agent.send(task)
        except RuntimeError as exc:
            events.record("subagent.error", name=self.name, error=str(exc))
            return ToolExecutionResult(str(exc), is_error=True)
        events.record("subagent.done", name=self.name)
        return ToolExecutionResult(result)
