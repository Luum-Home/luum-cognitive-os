"""MCP wrapper seam for the runtime lab.

This is intentionally a wrapper around a supplied client object. It does not
replace host/user MCP configuration; it shows how ADR-291 runtime tools can
adapt MCP tools into the same typed registry when service/headless execution is
explicitly enabled.
"""

from __future__ import annotations

from typing import Protocol

from agent_service.runtime_lab.approval import ApprovalPolicy
from agent_service.runtime_lab.debug import EventRecorder
from agent_service.runtime_lab.types import ToolDefinition, ToolExecutionResult


class MCPClient(Protocol):
    def call_tool(self, name: str, arguments: dict[str, object]) -> ToolExecutionResult:
        """Call a remote MCP tool and return a runtime-lab tool result."""


class MCPToolWrapper:
    def __init__(
        self,
        server_name: str,
        remote_name: str,
        description: str,
        input_schema: dict[str, object],
        required: list[str],
        client: MCPClient,
    ) -> None:
        self.server_name = server_name
        self.remote_name = remote_name
        self.description = description
        self.input_schema = dict(input_schema)
        self.required = list(required)
        self.client = client

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=f"{self.server_name}_{self.remote_name}",
            description=self.description,
            input_schema=self.input_schema,
            required=self.required,
        )

    def execute(
        self,
        payload: dict[str, object],
        approvals: ApprovalPolicy,
        events: EventRecorder,
    ) -> ToolExecutionResult:
        events.record(
            "mcp.tool.request",
            server=self.server_name,
            remote_name=self.remote_name,
        )
        result = self.client.call_tool(self.remote_name, payload)
        events.record(
            "mcp.tool.result",
            server=self.server_name,
            remote_name=self.remote_name,
            is_error=result.is_error,
        )
        return result
