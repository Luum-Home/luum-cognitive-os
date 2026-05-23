"""Runtime tool approval primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ApprovalRequest:
    tool_name: str
    tool_input: dict[str, object]
    prompt: str
    diff: str | None = None


@dataclass(frozen=True)
class ApprovalDecision:
    allowed: bool
    reason: str = ""


class ApprovalPolicy(Protocol):
    def approve(self, request: ApprovalRequest) -> ApprovalDecision:
        """Return whether a tool call may execute."""


class AlwaysAllowApproval:
    """Test/lab policy that records the approval boundary while allowing calls."""

    def approve(self, request: ApprovalRequest) -> ApprovalDecision:
        return ApprovalDecision(allowed=True, reason=f"allowed {request.tool_name}")


class DenyAllApproval:
    """Useful for tests that need to prove the denial path."""

    def approve(self, request: ApprovalRequest) -> ApprovalDecision:
        return ApprovalDecision(allowed=False, reason=f"denied {request.tool_name}")
