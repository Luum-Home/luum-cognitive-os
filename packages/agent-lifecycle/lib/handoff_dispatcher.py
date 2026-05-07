# SCOPE: both
"""ADR-230 handoff dispatcher with cycle/depth/permission gates."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from lib.handoff_envelope import HandoffEnvelope
from lib.session_bus import append_session_event

MAX_HANDOFF_DEPTH = 7
BLAST_RADIUS_OPERATOR_THRESHOLD = 50


class HandoffDispatchError(RuntimeError):
    """Base class for handoff dispatch failures."""


class HandoffCycleDetected(HandoffDispatchError):
    """Raised before delivery when the target already appears in call_chain."""

    def __init__(self, *, cycle: list[str], envelope: HandoffEnvelope) -> None:
        self.cycle = cycle
        self.envelope = envelope
        super().__init__("handoff cycle detected: " + " -> ".join(cycle))


class HandoffDepthExceeded(HandoffDispatchError):
    """Raised when the handoff chain exceeds the configured maximum depth."""

    def __init__(self, *, max_depth: int, envelope: HandoffEnvelope) -> None:
        self.max_depth = max_depth
        self.envelope = envelope
        super().__init__(f"handoff depth {envelope.depth} exceeds max {max_depth}")


class HandoffBlockedByOperator(HandoffDispatchError):
    """Raised when blast-radius policy requires approval and approval is absent."""

    def __init__(self, *, threshold: int, envelope: HandoffEnvelope) -> None:
        self.threshold = threshold
        self.envelope = envelope
        super().__init__(
            f"handoff blast radius {envelope.granted_blast_radius} exceeds threshold {threshold}"
        )


@dataclass(frozen=True)
class HandoffDispatchResult:
    """Result of an accepted or idempotently replayed handoff."""

    envelope: HandoffEnvelope
    events: list[dict[str, Any]]
    delivered: bool
    awaited_return: bool
    duplicate: bool = False


def _project_root(project_dir: str | Path | None) -> Path:
    return Path(project_dir or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()).resolve()


def _handoff_ledger_path(project_dir: str | Path | None, session_id: str | None) -> Path:
    sid = session_id or os.environ.get("COGNITIVE_OS_SESSION_ID") or os.environ.get("CODEX_SESSION_ID") or "unknown"
    safe_sid = sid.replace("/", "_").replace("\\", "_")
    return _project_root(project_dir) / ".cognitive-os" / "handoffs" / f"{safe_sid}.jsonl"


def _read_seen_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        handoff_id = record.get("handoff_id")
        if isinstance(handoff_id, str):
            seen.add(handoff_id)
    return seen


def _append_seen(path: Path, envelope: HandoffEnvelope) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"handoff_id": envelope.handoff_id, "to_agent": envelope.to_agent}, sort_keys=True) + "\n")


def _intersect_preserving_order(requested: list[str], accepted: list[str] | None) -> list[str]:
    if accepted is None:
        return list(requested)
    accepted_set = set(accepted)
    return [tool for tool in requested if tool in accepted_set]


class HandoffDispatcher:
    """Dependency-free dispatcher enforcing ADR-230 before delivery."""

    def __init__(
        self,
        *,
        project_dir: str | Path | None = None,
        session_id: str | None = None,
        max_handoff_depth: int = MAX_HANDOFF_DEPTH,
        blast_radius_threshold: int = BLAST_RADIUS_OPERATOR_THRESHOLD,
        receiver_tools: dict[str, list[str]] | None = None,
        event_sink: Callable[[str, dict[str, Any]], dict[str, Any] | None] | None = None,
        operator_approved: bool = False,
        persist_idempotency: bool = True,
    ) -> None:
        self.project_dir = project_dir
        self.session_id = session_id
        self.max_handoff_depth = max_handoff_depth
        self.blast_radius_threshold = blast_radius_threshold
        self.receiver_tools = receiver_tools or {}
        self.event_sink = event_sink
        self.operator_approved = operator_approved
        self.persist_idempotency = persist_idempotency
        self._memory_seen: set[str] = set()

    def _emit(self, event_type: str, envelope: HandoffEnvelope, **extra: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {"handoff": envelope.to_dict(), **extra}
        if self.event_sink is not None:
            event = self.event_sink(event_type, payload)
            return event or {"event_type": event_type, "payload": payload}
        if self.session_id:
            return append_session_event(
                event_type,
                payload,
                project_dir=self.project_dir,
                session_id=self.session_id,
                single_writer=True,
            )
        return {"event_type": event_type, "payload": payload}

    def _already_delivered(self, envelope: HandoffEnvelope) -> bool:
        if envelope.handoff_id in self._memory_seen:
            return True
        if not self.persist_idempotency:
            return False
        path = _handoff_ledger_path(self.project_dir, self.session_id)
        return envelope.handoff_id in _read_seen_ids(path)

    def _mark_delivered(self, envelope: HandoffEnvelope) -> None:
        self._memory_seen.add(envelope.handoff_id)
        if self.persist_idempotency:
            _append_seen(_handoff_ledger_path(self.project_dir, self.session_id), envelope)

    def dispatch(self, envelope: HandoffEnvelope) -> HandoffDispatchResult:
        """Validate, scope down, and deliver one envelope.

        Cycle detection intentionally runs before depth, permission intersection,
        blast-radius gates, and idempotency so a loop cannot trigger secondary
        side effects.
        """
        if envelope.to_agent in envelope.call_chain:
            cycle = envelope.call_chain + [envelope.to_agent]
            self._emit("handoff.cycle_detected", envelope, cycle=cycle)
            raise HandoffCycleDetected(cycle=cycle, envelope=envelope)

        if envelope.depth > self.max_handoff_depth:
            self._emit("handoff.depth_exceeded", envelope, max_depth=self.max_handoff_depth)
            raise HandoffDepthExceeded(max_depth=self.max_handoff_depth, envelope=envelope)

        if self._already_delivered(envelope):
            event = self._emit("handoff.idempotent_replay", envelope)
            return HandoffDispatchResult(
                envelope=envelope,
                events=[event],
                delivered=False,
                awaited_return=envelope.return_control,
                duplicate=True,
            )

        events: list[dict[str, Any]] = [self._emit("handoff.requested", envelope)]
        scoped = envelope.with_updates(granted_tools=[] if envelope.intent == "query" else envelope.granted_tools)
        accepted = self.receiver_tools.get(scoped.to_agent)
        intersected = _intersect_preserving_order(scoped.granted_tools, accepted)
        if intersected != scoped.granted_tools:
            before = list(scoped.granted_tools)
            scoped = scoped.with_updates(granted_tools=intersected)
            events.append(self._emit("handoff.permission.scoped_down", scoped, before=before, after=intersected))

        if scoped.granted_blast_radius > self.blast_radius_threshold and not self.operator_approved:
            events.append(
                self._emit("handoff.operator_blocked", scoped, threshold=self.blast_radius_threshold)
            )
            raise HandoffBlockedByOperator(threshold=self.blast_radius_threshold, envelope=scoped)

        events.append(self._emit("handoff.dispatched", scoped))
        self._mark_delivered(scoped)
        return HandoffDispatchResult(
            envelope=scoped,
            events=events,
            delivered=True,
            awaited_return=scoped.return_control,
        )


def dispatch_handoff(envelope: HandoffEnvelope, **kwargs: Any) -> HandoffDispatchResult:
    """Convenience wrapper around ``HandoffDispatcher(...).dispatch``."""
    return HandoffDispatcher(**kwargs).dispatch(envelope)
