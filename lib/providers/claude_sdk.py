# SCOPE: both
"""Claude Agent SDK provider wrapper (ADR-062 opt-in, ADR-063).

Uses the official Python `claude-agent-sdk` package (MIT license) to run
agent loops with the full Claude Code ecosystem: MCP protocol, session
persistence, in-process hooks, structured output.

This is opt-in tier-5 — requires ANTHROPIC_API_KEY and the `claude-agent-sdk`
Python package to be installed. Advance only on rate-limit errors (paid
per-token via Anthropic API — same policy as openai provider).

Installation:
    uv sync --extra claude-sdk
    # or: pip install claude-agent-sdk>=0.1

Configuration:
    ANTHROPIC_API_KEY  — from console.anthropic.com

When to use this provider (vs Claude Code native):
  - CI environments where Claude Code CLI is unavailable
  - Programmatic agent loops that need MCP or session persistence
  - Benchmarking / evaluation harnesses (ADR-052)

When NOT to use this provider:
  - Normal operator sessions (Claude Code native consumes subscription quota,
    not pay-per-token)
  - Batch/cron jobs (ToS: SDK requires interactive or API-keyed context)

Note on sdk package name:
  import name is `claude_agent_sdk` (underscores), pip/uv name is
  `claude-agent-sdk` (dashes). The try/except in is_configured() handles
  ImportError gracefully so the cascade skips this provider when the package
  is not installed.

Reference: docs/adrs/ADR-062-multi-provider-agent-loop.md
           docs/adrs/ADR-063-agent-tool-replication-strategy.md
           .cognitive-os/reports/claude-agent-sdk-surface-2026-04-24.md
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "claude-sonnet-4-6"  # cost-balanced default

MODEL_MAP: Dict[str, str] = {
    "opus":   "claude-opus-4-7",
    "sonnet": "claude-sonnet-4-6",
    "haiku":  "claude-haiku-3-5",
}

_COST_ESTIMATES: Dict[str, tuple[float, float]] = {
    "claude-opus-4-7":    (15.0,  75.0),
    "claude-sonnet-4-6":  (3.0,   15.0),
    "claude-haiku-3-5":   (0.25,   1.25),
}


# ── SDK import (optional dep) ─────────────────────────────────────────────────

def _sdk_available() -> bool:
    """True iff claude_agent_sdk is importable (package installed)."""
    try:
        import claude_agent_sdk  # type: ignore  # noqa: F401
        return True
    except ImportError:
        return False


# ── Provider interface ────────────────────────────────────────────────────────

def is_configured() -> bool:
    """True iff ANTHROPIC_API_KEY is set AND claude_agent_sdk is importable.

    Both conditions must hold: the key pays for the calls, the package provides
    the runner. Missing either means this provider cannot function.
    """
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return False
    return _sdk_available()


def get_client() -> Any:
    """Return the claude_agent_sdk module (not an OpenAI-compat client).

    The SDK does not expose a traditional client object — `query()` is the
    entry point. Returns the module itself so callers can invoke `query()`.
    Returns None if the SDK is not installed or API key is missing.
    """
    if not is_configured():
        return None
    try:
        import claude_agent_sdk  # type: ignore
        return claude_agent_sdk
    except ImportError:
        return None


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    rates = _COST_ESTIMATES.get(model)
    if rates is None:
        rates = _COST_ESTIMATES["claude-sonnet-4-6"]
    return (tokens_in * rates[0] + tokens_out * rates[1]) / 1_000_000


def call(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    timeout: float = 120.0,
    model_hint: Optional[str] = None,
    **kwargs: Any,
) -> dict:
    """Call claude-agent-sdk. Returns a normalized response dict.

    Converts OpenAI-format messages to SDK format, runs the agent loop,
    and collects the final response. Uses asyncio to run the async SDK.

    Advance policy: ONLY advance on rate-limit errors (paid per-token).

    Note: the SDK's `query()` returns an async iterator of messages. We
    consume it synchronously via asyncio.run() to match the synchronous
    interface expected by dispatch.py.
    """
    if model_hint:
        model = MODEL_MAP.get(model_hint, DEFAULT_MODEL)

    sdk = get_client()
    if sdk is None:
        return {
            "success": False,
            "text": "",
            "model": model,
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "error": (
                "claude_sdk unavailable: ANTHROPIC_API_KEY unset or "
                "claude-agent-sdk not installed (uv sync --extra claude-sdk)"
            ),
        }

    # Convert messages to the task string the SDK expects.
    # SDK query() takes a task (str) + options — we flatten the message history
    # into a single user prompt, honoring any system message first.
    system_parts: List[str] = []
    user_parts: List[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_parts.append(content)
        elif role == "user":
            user_parts.append(content)
        elif role == "assistant":
            user_parts.append(f"[Assistant previously said: {content}]")

    task = "\n\n".join(user_parts) if user_parts else ""
    system_prompt = "\n\n".join(system_parts) if system_parts else None

    async def _run() -> dict:
        try:
            # Build options — sdk.ClaudeAgentOptions or dict (depends on SDK version)
            opts: Dict[str, Any] = {
                "model": model,
                "max_turns": 1,  # single-turn for compatibility with dispatch.py interface
            }
            if system_prompt:
                opts["system_prompt"] = system_prompt
            if max_tokens is not None:
                opts["max_tokens"] = max_tokens

            text_parts: List[str] = []
            ti = to = 0
            cost = 0.0

            async for msg_obj in sdk.query(prompt=task, options=opts):
                msg_type = type(msg_obj).__name__
                if msg_type == "AssistantMessage":
                    content = getattr(msg_obj, "content", None)
                    if isinstance(content, list):
                        for block in content:
                            if getattr(block, "type", "") == "text":
                                text_parts.append(getattr(block, "text", ""))
                    elif isinstance(content, str):
                        text_parts.append(content)
                elif msg_type == "ResultMessage":
                    usage = getattr(msg_obj, "usage", None)
                    if usage:
                        ti = getattr(usage, "input_tokens", 0) or 0
                        to = getattr(usage, "output_tokens", 0) or 0
                    cost = float(getattr(msg_obj, "total_cost_usd", 0.0) or 0.0)

            final_text = "\n".join(text_parts).strip()
            return {
                "success": True,
                "text": final_text,
                "model": model,
                "tokens_in": ti,
                "tokens_out": to,
                "cost_usd": cost if cost > 0.0 else estimate_cost(model, ti, to),
                "error": "",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "text": "",
                "model": model,
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "error": str(exc)[:500],
            }

    # Run the async function synchronously.
    # If there's already an event loop running (e.g., in pytest-asyncio), use
    # a new thread to avoid "cannot run nested event loops".
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(asyncio.run, _run())
                return future.result(timeout=timeout)
        else:
            return loop.run_until_complete(_run())
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "text": "",
            "model": model,
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "error": f"asyncio error: {exc!r}"[:500],
        }
