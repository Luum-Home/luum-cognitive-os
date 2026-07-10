# SCOPE: os-only
"""Read-only capability-ceiling signal detection.

This module classifies typed capability ceiling signals emitted by an agent and
turns them into a structured handoff for an orchestrator. It intentionally does
not re-launch agents, change retry budgets, or account for escalation costs.
Those scopes belong to ADR-228 and future dispatch orchestration work.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class CapabilitySignal(str, Enum):
    """Typed capability ceiling signal vocabulary."""

    NEEDS_DEEPER_REASONING = "NEEDS_DEEPER_REASONING"
    NEEDS_TOOL_ACCESS = "NEEDS_TOOL_ACCESS"
    NEEDS_MORE_CONTEXT = "NEEDS_MORE_CONTEXT"
    NEEDS_DOMAIN_EXPERT = "NEEDS_DOMAIN_EXPERT"


RECOMMENDED_ACTION_BY_SIGNAL: dict[CapabilitySignal, str] = {
    CapabilitySignal.NEEDS_DEEPER_REASONING: "upgrade_model",
    CapabilitySignal.NEEDS_TOOL_ACCESS: "grant_tool_or_human_review",
    CapabilitySignal.NEEDS_MORE_CONTEXT: "expand_context",
    CapabilitySignal.NEEDS_DOMAIN_EXPERT: "route_domain_expert",
}

CAPABILITY_BY_SIGNAL: dict[CapabilitySignal, str] = {
    CapabilitySignal.NEEDS_DEEPER_REASONING: "reasoning",
    CapabilitySignal.NEEDS_TOOL_ACCESS: "tool_access",
    CapabilitySignal.NEEDS_MORE_CONTEXT: "context_window",
    CapabilitySignal.NEEDS_DOMAIN_EXPERT: "domain_expertise",
}

_FIELD_RE = re.compile(r"^\s*([A-Za-z_ -]+):\s*(.*?)\s*$")


@dataclass(frozen=True)
class CapabilityHandoff:
    """Structured handoff produced from an agent capability ceiling signal."""

    signal: CapabilitySignal
    capability: str
    recommended_action: str
    context_summary: str
    attempted: str = ""
    partial_result: str = ""
    original_task: str = ""
    source_agent_id: str = ""
    auto_redispatch_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable handoff fields."""
        data = asdict(self)
        data["signal"] = self.signal.value
        return data


def detect_capability_ceiling(
    agent_output: str,
    *,
    original_task: str = "",
    source_agent_id: str = "",
) -> CapabilityHandoff | None:
    """Classify a typed capability-ceiling signal from agent output.

    Detection is read-only: this function returns a handoff object and never
    dispatches, retries, imports dispatch helpers, writes metrics, or mutates
    process environment.
    """
    fields = _parse_escalation_fields(agent_output)
    signal = _extract_signal(agent_output, fields)
    if signal is None:
        return None

    capability = fields.get("capability") or CAPABILITY_BY_SIGNAL[signal]
    recommended_action = (
        fields.get("recommended_action")
        or fields.get("recommendation")
        or RECOMMENDED_ACTION_BY_SIGNAL[signal]
    )
    context_summary = fields.get("context_summary") or fields.get("context") or ""

    return CapabilityHandoff(
        signal=signal,
        capability=capability,
        recommended_action=recommended_action,
        context_summary=context_summary,
        attempted=fields.get("attempted", ""),
        partial_result=fields.get("partial_result", ""),
        original_task=original_task,
        source_agent_id=source_agent_id,
        auto_redispatch_allowed=False,
    )


def _extract_signal(
    agent_output: str, fields: dict[str, str]
) -> CapabilitySignal | None:
    typed_value = fields.get("type") or fields.get("signal")
    if typed_value:
        normalized = typed_value.strip().upper().replace("-", "_").replace(" ", "_")
        for signal in CapabilitySignal:
            if normalized == signal.value:
                return signal

    upper_output = agent_output.upper()
    matches = [signal for signal in CapabilitySignal if signal.value in upper_output]
    if len(matches) == 1:
        return matches[0]
    return None


def _parse_escalation_fields(agent_output: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    in_block = False
    current_key = ""

    for raw_line in agent_output.splitlines():
        if raw_line.strip().upper() == "ESCALATION:":
            in_block = True
            current_key = ""
            continue
        if not in_block:
            continue
        if raw_line and not raw_line.startswith((" ", "\t")) and ":" not in raw_line:
            break

        match = _FIELD_RE.match(raw_line)
        if match:
            key = match.group(1).strip().lower().replace(" ", "_").replace("-", "_")
            fields[key] = match.group(2).strip()
            current_key = key
        elif current_key and raw_line.strip():
            fields[current_key] = f"{fields[current_key]} {raw_line.strip()}".strip()

    return fields
