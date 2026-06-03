"""Dispatch entry point for ADR-033 harness-agnostic event capture.

Usage from a shell hook:

    python3 -c "import sys; from lib.harness_adapter.dispatch import handle_event; \
        handle_event(sys.stdin.read())"

or as a module import::

    from lib.harness_adapter.dispatch import handle_event
    handle_event(raw_payload)

The dispatcher:
    1. Decodes the raw payload (string → JSON dict if needed).
    2. Iterates registered adapters and picks the first whose
       :meth:`HarnessAdapter.detect_harness` returns a name.
    3. Calls :meth:`HarnessAdapter.parse_event` → list of canonical events.
    4. Emits each event via :meth:`HarnessAdapter.emit_canonical`.
    5. For :class:`HeartbeatTick` from the Claude Code adapter, also notifies
       legacy consumers through :meth:`ClaudeCodeAdapter.emit_heartbeat_legacy`
       so ``agent-heartbeat.jsonl`` stays schema-compatible with
       ``AgentBusMetrics.on_heartbeat_event``.

Failures are swallowed — capture must never block a hook. Callers that need
assertions (tests) can use :func:`dispatch_event` which returns structured
results instead.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Type

from .aider import AiderAdapter
from .bare_cli import BareCliAdapter
from .base import CanonicalEvent, HarnessAdapter, HeartbeatTick
from .claude_code import ClaudeCodeAdapter
from .codex import CodexAdapter
from .opencode import OpenCodeAdapter

#: Order matters: more-specific adapters go first.
#: BareCliAdapter is last — it acts as a fallback when no other adapter claims
#: the payload (its detect_harness uses a no-other-harness-env-vars heuristic).
ADAPTERS: List[Type[HarnessAdapter]] = [
    OpenCodeAdapter,
    CodexAdapter,
    ClaudeCodeAdapter,
    AiderAdapter,
    BareCliAdapter,
]


def _decode(raw: Any) -> Optional[Dict[str, Any]]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _project_dir() -> Path:
    return Path(
        os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )


def _pick_adapter(
    payload: Dict[str, Any],
    adapters: Sequence[Type[HarnessAdapter]],
    project_dir: Path,
) -> Optional[HarnessAdapter]:
    for cls in adapters:
        try:
            if cls.detect_harness(payload) is not None:
                supports_payload = getattr(cls, "supports_payload", None)
                if callable(supports_payload) and not supports_payload(payload):
                    continue
                return cls(project_dir=project_dir)
        except Exception:
            continue
    return None


def _context_ids(
    events: Sequence[CanonicalEvent], payload: Dict[str, Any]
) -> tuple[Optional[str], Optional[str]]:
    """Extract best-effort agent/session identifiers for inbound delivery."""
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    for evt in events:
        if agent_id is None and hasattr(evt, "agent_id"):
            value = getattr(evt, "agent_id")
            if value:
                agent_id = str(value)
        if session_id is None and hasattr(evt, "session_id"):
            value = getattr(evt, "session_id")
            if value:
                session_id = str(value)
    if agent_id is None:
        for key in ("agent_id", "tool_use_id", "call_id", "id"):
            value = payload.get(key)
            if value:
                agent_id = str(value)
                break
    if session_id is None:
        for key in ("session_id", "codex_session_id", "codex_thread_id", "opencode_session_id"):
            value = payload.get(key)
            if value:
                session_id = str(value)
                break
    return agent_id, session_id


def dispatch_event(
    raw: Any,
    *,
    adapters: Optional[Sequence[Type[HarnessAdapter]]] = None,
    project_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Decode, route, and emit. Return a structured result for tests.

    ``result`` keys:
        - ``harness``: :class:`HarnessName` value or ``"none"`` if nothing matched
        - ``events``: list of emitted :class:`CanonicalEvent` dicts
        - ``output_path``: resolved JSONL path (if any events were emitted)
    """
    payload = _decode(raw)
    if payload is None:
        return {"harness": "none", "events": [], "output_path": None}

    project = project_dir or _project_dir()
    pool = adapters or ADAPTERS
    adapter = _pick_adapter(payload, pool, project)
    if adapter is None:
        return {"harness": "none", "events": [], "output_path": None}

    try:
        canonical_events = adapter.parse_event(payload)
    except Exception:
        canonical_events = []

    # Inbound side: after parsing outbound telemetry, surface any pending
    # filesystem fallback control/answer/interrupt signals for this adapter
    # context.  This keeps harness adapters bidirectional even without Valkey.
    agent_id, session_id = _context_ids(canonical_events, payload)
    try:
        canonical_events = list(canonical_events) + list(
            adapter.parse_inbound_signals(agent_id=agent_id, session_id=session_id)
        )
    except Exception:
        canonical_events = list(canonical_events)

    emitted: List[Dict[str, Any]] = []
    output_path: Optional[str] = None
    for evt in canonical_events:
        try:
            path = adapter.emit_canonical(evt)
            output_path = str(path)
            emitted.append(evt.to_dict())
        except Exception:
            continue

        # Backwards compat: CC heartbeat events feed AgentBusMetrics AND
        # the FallbackBus per-agent heartbeat.jsonl that predates ADR-033.
        if isinstance(adapter, ClaudeCodeAdapter) and isinstance(evt, HeartbeatTick):
            adapter.emit_fallback_bus_legacy(evt)
            adapter.emit_heartbeat_legacy(evt)

    return {
        "harness": adapter.name.value,
        "events": emitted,
        "output_path": output_path,
    }


def handle_event(raw: Any) -> None:
    """Fire-and-forget entry point for shell hooks. Never raises."""
    try:
        dispatch_event(raw)
    except Exception:
        # Hooks must never fail because of observability.
        pass
