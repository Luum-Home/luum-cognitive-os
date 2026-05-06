# SCOPE: both
"""Hook definition types for COS (ADR-178).

Ports HttpHookDefinition and PromptHookDefinition from HKUDS/OpenHarness
(commit 7873f0d109174a57b3b1af7aa5397a6b3b0bd551, src/openharness/hooks/schemas.py)
under MIT licence, adapted to COS conventions.

Three hook types are provided:
  - ShellHookDefinition  — wraps existing COS shell-command hook (backward-compat)
  - HttpHookDefinition   — fires an HTTP callback with the event payload
  - PromptHookDefinition — invokes an inline LLM agent as a hook

NOTE: HttpHookDefinition and PromptHookDefinition are DECLARED here as first-class
types but are NOT yet wired into the COS hook dispatcher. Activation is gated on
ADR-178 §Future Work. Operators can reference the types in cognitive-os.yaml hook
blocks; the dispatcher will skip unknown types gracefully until wired.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from string import Template
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


@dataclass
class HookDefinition(ABC):
    """Abstract base for all COS hook definition types."""

    block_on_failure: bool = False
    matcher: str | None = None  # event-name glob filter (e.g. "PostToolUse")

    @abstractmethod
    def hook_type(self) -> str:
        """Return the canonical type discriminator string."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> "HookDefinition":
        """Construct a hook definition from a plain dict (e.g. YAML config)."""


# ---------------------------------------------------------------------------
# ShellHookDefinition — backward-compatible wrapper for existing COS hooks
# ---------------------------------------------------------------------------


@dataclass
class ShellHookDefinition(HookDefinition):
    """A hook that executes a shell command (existing COS contract).

    Fields mirror the existing settings.json hook entries so that the dispatcher
    can round-trip between this type and the raw dict without data loss.
    """

    command: str = ""
    timeout_seconds: int = 30

    def hook_type(self) -> str:
        return "command"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShellHookDefinition":
        return cls(
            command=data.get("command", ""),
            timeout_seconds=int(data.get("timeout_seconds", 30)),
            block_on_failure=bool(data.get("block_on_failure", False)),
            matcher=data.get("matcher"),
        )


# ---------------------------------------------------------------------------
# HttpHookDefinition — ported from OpenHarness schemas.py (MIT)
# ---------------------------------------------------------------------------
#
# Upstream fields (verbatim where possible):
#   type: Literal["http"]
#   url: str
#   headers: dict[str, str]
#   timeout_seconds: int  (we add timeout_ms as primary; timeout_seconds derived)
#   matcher: str | None
#   block_on_failure: bool
#
# COS additions:
#   method: str           — HTTP verb (POST default)
#   body_template: str    — str.Template body; $payload replaced with JSON payload
#   expected_status: set  — acceptable HTTP status codes


@dataclass
class HttpHookDefinition(HookDefinition):
    """A hook that POSTs (or otherwise sends) the event payload to an HTTP endpoint.

    Ported from HKUDS/OpenHarness commit 7873f0d109174a57b3b1af7aa5397a6b3b0bd551
    (src/openharness/hooks/schemas.py: HttpHookDefinition).

    COS adds: method, timeout_ms, body_template, expected_status.
    The upstream 'timeout_seconds' is preserved as a derived property for compat.
    """

    url: str = ""
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=dict)
    timeout_ms: int = 5000  # COS default; upstream default was 30s
    body_template: str = "$payload"  # str.Template; $payload = JSON-serialised event
    expected_status: frozenset[int] = field(
        default_factory=lambda: frozenset({200, 201, 202, 204})
    )
    block_on_failure: bool = False  # matches upstream default

    def hook_type(self) -> str:
        return "http"

    @property
    def timeout_seconds(self) -> int:
        """Derived from timeout_ms for compatibility with OpenHarness interface."""
        return max(1, self.timeout_ms // 1000)

    def render_body(self, payload_json: str) -> str:
        """Render body_template substituting $payload with the serialised event."""
        return Template(self.body_template).safe_substitute(payload=payload_json)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HttpHookDefinition":
        raw_status = data.get("expected_status", [200, 201, 202, 204])
        if isinstance(raw_status, int):
            raw_status = [raw_status]
        return cls(
            url=data.get("url", ""),
            method=str(data.get("method", "POST")).upper(),
            headers=dict(data.get("headers", {})),
            timeout_ms=int(data.get("timeout_ms", data.get("timeout_seconds", 5) * 1000)),
            body_template=str(data.get("body_template", "$payload")),
            expected_status=frozenset(int(s) for s in raw_status),
            block_on_failure=bool(data.get("block_on_failure", False)),
            matcher=data.get("matcher"),
        )


# ---------------------------------------------------------------------------
# PromptHookDefinition — ported from OpenHarness schemas.py (MIT)
# ---------------------------------------------------------------------------
#
# Upstream fields (verbatim where possible):
#   type: Literal["prompt"]
#   prompt: str
#   model: str | None
#   timeout_seconds: int
#   matcher: str | None
#   block_on_failure: bool
#
# COS additions:
#   prompt_template: str  — richer template (upstream used `prompt`)
#   model_hint: str       — haiku/sonnet/opus tier (maps via MODEL_MAP)
#   inline_agent_subagent_type: str  — passed to CC subagent spawn
#   max_tokens: int


@dataclass
class PromptHookDefinition(HookDefinition):
    """A hook that asks an inline LLM agent to validate a condition.

    Ported from HKUDS/OpenHarness commit 7873f0d109174a57b3b1af7aa5397a6b3b0bd551
    (src/openharness/hooks/schemas.py: PromptHookDefinition).

    COS adds: prompt_template, model_hint, inline_agent_subagent_type, max_tokens.
    The upstream 'prompt' field is aliased to prompt_template for compat.
    """

    prompt_template: str = ""  # Template text; $event_json substituted at runtime
    model_hint: Literal["haiku", "sonnet", "opus"] | None = "haiku"
    inline_agent_subagent_type: str = "inline"  # passed to subagent spawn
    max_tokens: int = 256
    timeout_seconds: int = 30  # matches upstream default
    block_on_failure: bool = True  # matches upstream default (conservative)

    def hook_type(self) -> str:
        return "prompt"

    @property
    def prompt(self) -> str:
        """Alias for upstream interface compatibility."""
        return self.prompt_template

    def render_prompt(self, event_json: str) -> str:
        """Render prompt_template substituting $event_json."""
        return Template(self.prompt_template).safe_substitute(event_json=event_json)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromptHookDefinition":
        hint = data.get("model_hint") or data.get("model") or "haiku"
        if hint not in ("haiku", "sonnet", "opus"):
            hint = "haiku"
        return cls(
            prompt_template=data.get("prompt_template") or data.get("prompt", ""),
            model_hint=hint,  # type: ignore[arg-type]
            inline_agent_subagent_type=str(
                data.get("inline_agent_subagent_type", "inline")
            ),
            max_tokens=int(data.get("max_tokens", 256)),
            timeout_seconds=int(data.get("timeout_seconds", 30)),
            block_on_failure=bool(data.get("block_on_failure", True)),
            matcher=data.get("matcher"),
        )


# ---------------------------------------------------------------------------
# Factory — deserialise from dict (dispatches on "type" key)
# ---------------------------------------------------------------------------

_TYPE_MAP: dict[str, type[HookDefinition]] = {
    "command": ShellHookDefinition,
    "shell": ShellHookDefinition,  # alias
    "http": HttpHookDefinition,
    "prompt": PromptHookDefinition,
}


def hook_from_dict(data: dict[str, Any]) -> HookDefinition:
    """Deserialise a hook definition dict (from YAML / settings.json).

    Falls back to ShellHookDefinition for legacy entries that lack a 'type' key
    but have a 'command' key (backward-compatible with existing COS hooks).
    """
    hook_type_key = str(data.get("type", "command" if "command" in data else "")).lower()
    cls = _TYPE_MAP.get(hook_type_key)
    if cls is None:
        raise ValueError(
            f"Unknown hook type '{hook_type_key}'. "
            f"Expected one of: {sorted(_TYPE_MAP)}."
        )
    return cls.from_dict(data)
