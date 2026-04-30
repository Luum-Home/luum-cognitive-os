"""Harness adapter ABC + canonical event schema (ADR-033).

This module defines the portable event vocabulary that any supported LLM-agent
harness (Claude Code, OpenCode, Aider, Cursor, Continue, ...) must translate
into. Downstream consumers (AgentBusMetrics, cost dashboards, SLO probes) only
see :class:`CanonicalEvent` subclasses and therefore stay harness-agnostic.

Design goals:
- Zero third-party dependencies (stdlib only).
- Dataclasses with ``to_dict`` / ``from_dict`` roundtrip for JSONL emission.
- ``HarnessAdapter`` is intentionally thin: detect → parse → emit.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Type


# ---------------------------------------------------------------------------
# Harness identity
# ---------------------------------------------------------------------------


class HarnessName(str, Enum):
    """Known agent harnesses. Extend when adding a new adapter."""

    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    OPENCODE = "opencode"
    AIDER = "aider"
    CURSOR = "cursor"
    CONTINUE = "continue"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Canonical event schema
# ---------------------------------------------------------------------------


@dataclass
class CanonicalEvent:
    """Base class for all canonical events.

    Subclasses set :attr:`event_type` as a class variable. ``to_dict`` flattens
    dataclass fields and injects ``event_type`` so JSONL consumers can dispatch.
    """

    event_type: ClassVar[str] = "canonical"

    # Registry of event_type -> subclass, populated by __init_subclass__.
    _registry: ClassVar[Dict[str, Type["CanonicalEvent"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.event_type != "canonical":
            CanonicalEvent._registry[cls.event_type] = cls

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["event_type"] = self.event_type
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CanonicalEvent":
        """Reconstruct a canonical event from a dict.

        Uses the ``event_type`` field to pick the right subclass. Falls back to
        ``cls`` (which may be the base class, useful for generic round-tripping).
        """
        event_type = data.get("event_type", cls.event_type)
        target = CanonicalEvent._registry.get(event_type, cls)
        payload = {k: v for k, v in data.items() if k != "event_type"}
        valid = {f.name for f in fields(target)}
        filtered = {k: v for k, v in payload.items() if k in valid}
        return target(**filtered)  # type: ignore[arg-type]


@dataclass
class SessionStart(CanonicalEvent):
    """Emitted when a harness session begins."""

    event_type: ClassVar[str] = "session_start"

    session_id: str = ""
    started_at: float = 0.0
    harness: str = ""
    cwd: Optional[str] = None
    source: Optional[str] = None
    version: Optional[str] = None


@dataclass
class UserPromptSubmit(CanonicalEvent):
    """Emitted when a user prompt enters the harness."""

    event_type: ClassVar[str] = "user_prompt_submit"

    session_id: Optional[str] = None
    submitted_at: float = 0.0
    harness: str = ""
    prompt_summary: Optional[str] = None
    prompt_hash: Optional[str] = None


@dataclass
class SessionEnd(CanonicalEvent):
    """Emitted when a harness session or turn completes."""

    event_type: ClassVar[str] = "session_end"

    session_id: str = ""
    ended_at: float = 0.0
    harness: str = ""
    exit_status: str = "unknown"
    duration_ms: Optional[int] = None


@dataclass
class AgentStart(CanonicalEvent):
    """Emitted when a sub-agent / tool-use with agent-semantics begins."""

    event_type: ClassVar[str] = "agent_start"

    agent_id: str = ""
    started_at: float = 0.0
    tool_name: str = "Agent"
    model: Optional[str] = None
    cwd: Optional[str] = None
    parent_id: Optional[str] = None
    input_summary: Optional[str] = None
    session_id: Optional[str] = None
    # ADR-038 Gap #4: cap on reasoning cycles per agent task (default 20).
    # Kept optional so existing callers that omit the field stay backward compat.
    max_reasoning_cycles: int = 20


@dataclass
class AgentEnd(CanonicalEvent):
    """Emitted when a sub-agent terminates (success or failure)."""

    event_type: ClassVar[str] = "agent_end"

    agent_id: str = ""
    ended_at: float = 0.0
    exit_status: str = "unknown"  # "success" | "error" | "timeout" | "unknown"
    duration_ms: Optional[int] = None
    token_usage: Dict[str, int] = field(default_factory=dict)  # input/output/cached
    cost_usd: Optional[float] = None
    session_id: Optional[str] = None


@dataclass
class ToolUse(CanonicalEvent):
    """Generic tool invocation (Read, Write, Bash, Grep, ...)."""

    event_type: ClassVar[str] = "tool_use"

    agent_id: str = ""
    tool_name: str = ""
    started_at: float = 0.0
    duration_ms: Optional[int] = None
    exit_status: str = "unknown"
    tool_input_hash: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class TokenUsage(CanonicalEvent):
    """Token accounting snapshot (often coincides with AgentEnd)."""

    event_type: ClassVar[str] = "token_usage"

    agent_id: str = ""
    ts: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: Optional[int] = None
    cache_creation: Optional[int] = None
    model: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class HeartbeatTick(CanonicalEvent):
    """Liveness tick — maps to SLO 9 / agent-heartbeat.jsonl."""

    event_type: ClassVar[str] = "heartbeat_tick"

    agent_id: str = ""
    ts: float = 0.0
    alive: bool = True
    tool_call_count: Optional[int] = None
    remaining_budget: Optional[float] = None
    session_id: Optional[str] = None
    # ADR-038 Gap #4: cumulative PostToolUse:Agent events seen for this agent_id
    # within the current session. None means "not tracked" (backward compat).
    reasoning_cycle_count: Optional[int] = None


@dataclass
class ToolUseStart(CanonicalEvent):
    """Emitted when a specific tool invocation begins (ADR-034 live events).

    Distinct from :class:`ToolUse` (which is a combined start+end record emitted
    post-hoc by the Claude Code adapter). ``ToolUseStart`` is used by streaming
    adapters that can detect the *beginning* of a tool call in real-time.
    """

    event_type: ClassVar[str] = "tool_use_start"

    agent_id: str = ""
    tool_name: str = ""
    started_at: float = 0.0
    tool_input_summary: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class ToolUseEnd(CanonicalEvent):
    """Emitted when a specific tool invocation completes (ADR-034 live events).

    Pairs with :class:`ToolUseStart`. Streaming adapters emit this when they
    detect the end of a tool call (e.g. Aider's "Ran shell command" line).
    """

    event_type: ClassVar[str] = "tool_use_end"

    agent_id: str = ""
    tool_name: str = ""
    ended_at: float = 0.0
    duration_ms: Optional[int] = None
    exit_status: str = "unknown"
    session_id: Optional[str] = None


@dataclass
class ProgressMarker(CanonicalEvent):
    """Emitted when a ``PROGRESS: [N/M] message`` line is detected (ADR-034).

    Sub-agents are required by ``rules/responsiveness.md`` to emit PROGRESS
    markers so the orchestrator can track live execution. Streaming adapters
    translate these into :class:`ProgressMarker` canonical events for
    downstream consumers (Agent Bus, SLO probes, dashboards).
    """

    event_type: ClassVar[str] = "progress_marker"

    agent_id: str = ""
    ts: float = 0.0
    step_current: int = 0
    step_total: int = 0
    message: str = ""
    session_id: Optional[str] = None


@dataclass
class ParseError(CanonicalEvent):
    """Emitted when a line does not match any known pattern in a passive adapter.

    ADR-033b: replaces silent skips in Aider version dispatch. Consumers can
    filter on ``event_type == "parse_error"`` to track unknown transcript formats.
    """

    event_type: ClassVar[str] = "parse_error"

    source_line: str = ""
    adapter: str = ""
    reason: str = ""
    session_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Adapter ABC
# ---------------------------------------------------------------------------


class HarnessAdapter(ABC):
    """Translate harness-specific raw events into canonical events.

    Implementations live next to this file (e.g. ``claude_code.py``,
    ``aider.py``). Dispatch is done by ``dispatch.handle_event``.
    """

    #: Canonical :class:`HarnessName` this adapter targets.
    name: ClassVar[HarnessName] = HarnessName.UNKNOWN

    #: Default JSONL destination for :meth:`emit_canonical`. Subclasses MAY
    #: override. The dispatch layer resolves this relative to the project dir.
    default_output: ClassVar[str] = ".cognitive-os/metrics/canonical-events.jsonl"

    def __init__(self, project_dir: Optional[Path] = None) -> None:
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()

    # --------------------------- public API --------------------------------

    @classmethod
    @abstractmethod
    def detect_harness(cls, raw: Any) -> Optional[HarnessName]:
        """Return this adapter's :class:`HarnessName` iff ``raw`` looks native.

        ``raw`` is typically the stdin payload handed to a hook, or a file-path
        for passive file-watching adapters. Returning ``None`` means "not me".
        """

    @abstractmethod
    def parse_event(self, raw: Dict[str, Any]) -> List[CanonicalEvent]:
        """Translate one harness-native payload into 0+ canonical events.

        A single harness event may fan out to multiple canonical events (e.g. a
        PostToolUse:Agent carries both :class:`AgentEnd` and
        :class:`TokenUsage`).
        """

    def emit_canonical(
        self,
        event: CanonicalEvent,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Append ``event`` as one JSON line to the configured JSONL file.

        Returns the resolved output path for caller convenience.
        """
        target = Path(output_path) if output_path else (
            self.project_dir / self.default_output
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(event.to_json() + "\n")
        return target


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def now_epoch() -> float:
    """Monotonic-friendly wall-clock timestamp used across adapters."""
    return time.time()
