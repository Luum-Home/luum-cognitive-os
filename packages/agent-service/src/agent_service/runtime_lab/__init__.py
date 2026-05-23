"""COS native agent-runner lab for ADR-291 runtime slices.

This package is intentionally local to agent-service. It models an owned agent
loop without replacing Cognitive OS harness-driver governance.
"""

from agent_service.runtime_lab.agent import Agent
from agent_service.runtime_lab.approval import (
    AlwaysAllowApproval,
    ApprovalDecision,
    DenyAllApproval,
)
from agent_service.runtime_lab.compaction import SafeSlidingWindow, safe_split_point
from agent_service.runtime_lab.debug import EventRecorder, RuntimeEvent
from agent_service.runtime_lab.llm import MockLLMProvider
from agent_service.runtime_lab.tools import EchoTool, ToolRegistry, WriteFileTool
from agent_service.runtime_lab.types import Block, BlockType, Message, Role

__all__ = [
    "Agent",
    "AlwaysAllowApproval",
    "ApprovalDecision",
    "Block",
    "BlockType",
    "DenyAllApproval",
    "EchoTool",
    "EventRecorder",
    "Message",
    "MockLLMProvider",
    "Role",
    "RuntimeEvent",
    "SafeSlidingWindow",
    "ToolRegistry",
    "WriteFileTool",
    "safe_split_point",
]
