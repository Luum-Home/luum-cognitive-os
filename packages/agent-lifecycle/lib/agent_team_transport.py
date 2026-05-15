# SCOPE: both
"""ADR-233 transport upgrade descriptors for agent-team file IPC.

The default transport remains local file IPC.  This module deliberately does not
import NATS/A2A clients; it gives operators and future adapters a machine-
readable migration contract without adding daemons or dependencies.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import urllib.request
from collections.abc import Coroutine
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = "agent-team-transport-plan/v1"


@dataclass(frozen=True)
class TransportPlan:
    schema_version: str
    backend: str
    status: str
    dependency_policy: str
    subject_mapping: dict[str, str]
    compatibility: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def transport_plan(*, team_name: str, backend: str = "file") -> TransportPlan:
    """Return the canonical ADR-233 transport mapping for a backend.

    Supported backends are declarative only except ``file``.  ``nats`` and
    ``a2a`` are upgrade targets whose subjects/parts preserve the same team
    semantics, making migration testable before adopting external infra.
    """
    if not team_name or "/" in team_name or "\\" in team_name:
        raise ValueError(f"unsafe team_name: {team_name!r}")
    normalized = backend.strip().lower()
    if normalized not in {"file", "nats", "a2a"}:
        raise ValueError("backend must be one of: file, nats, a2a")
    base = {
        "members": f"cos.teams.{team_name}.members",
        "tasks": f"cos.teams.{team_name}.tasks",
        "inbox": f"cos.teams.{team_name}.inbox.<session_id>",
        "events": f"cos.teams.{team_name}.events",
        "handoffs": f"cos.teams.{team_name}.handoffs.<session_id>",
    }
    if normalized == "file":
        return TransportPlan(
            schema_version=SCHEMA_VERSION,
            backend="file",
            status="active",
            dependency_policy="default-zero-dependency-file-ipc",
            subject_mapping={
                "members": ".cognitive-os/teams/{team}/members.jsonl",
                "tasks": ".cognitive-os/teams/{team}/tasks.jsonl",
                "inbox": ".cognitive-os/teams/{team}/inbox/{session_id}.jsonl",
                "events": ".cognitive-os/teams/{team}/events.jsonl",
                "handoffs": ".cognitive-os/teams/{team}/inbox/{session_id}.jsonl:type=handoff",
            },
            compatibility={"lossless_to": ["nats", "a2a"], "ordering": "per-file lock", "requires_daemon": False},
        )
    if normalized == "nats":
        return TransportPlan(
            schema_version=SCHEMA_VERSION,
            backend="nats",
            status="upgrade_target",
            dependency_policy="opt-in-only; no NATS dependency in default COS install",
            subject_mapping=base,
            compatibility={"maps_from_file_ipc": True, "ordering": "per-subject stream", "requires_daemon": True},
        )
    return TransportPlan(
        schema_version=SCHEMA_VERSION,
        backend="a2a",
        status="upgrade_target",
        dependency_policy="opt-in-only; no A2A SDK dependency in default COS install",
        subject_mapping={
            "members": "A2A capability advertisement: team.members",
            "tasks": "A2A task artifact: team.tasks",
            "inbox": "A2A message part: recipient=<session_id>",
            "events": "A2A event stream: team.events",
            "handoffs": "A2A message part carrying handoff-envelope/v1",
        },
        compatibility={"maps_from_file_ipc": True, "ordering": "conversation/thread order", "requires_daemon": False},
    )


@dataclass(frozen=True)
class TransportSendResult:
    schema_version: str
    backend: str
    destination: str
    delivered: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def _run_awaitable(value: Any) -> Any:
    if not inspect.isawaitable(value):
        return value
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        if not isinstance(value, Coroutine):
            raise RuntimeError("async NATS operation returned non-coroutine awaitable")
        return asyncio.run(value)
    if loop.is_running():
        raise RuntimeError("async NATS operation returned awaitable inside a running loop; use async_send_inbox")
    return loop.run_until_complete(value)


class NatsAgentTeamTransport:
    """Opt-in NATS transport for ADR-233 messages.

    The adapter is real but dependency-free by default: pass an already-created
    NATS client in tests/operators, or use ``connect()`` when ``nats-py`` is
    installed. The expected client surface is ``publish(subject, bytes)``.
    """

    def __init__(self, *, team_name: str, client: Any) -> None:
        self.team_name = team_name
        self.client = client
        self.plan = transport_plan(team_name=team_name, backend="nats")

    @classmethod
    async def connect(cls, *, team_name: str, servers: list[str] | None = None) -> "NatsAgentTeamTransport":
        try:
            import nats  # type: ignore
        except ImportError as exc:
            raise RuntimeError("nats-py is not installed; install optional NATS adapter dependency") from exc
        client = await nats.connect(servers=servers or ["nats://127.0.0.1:4222"])
        return cls(team_name=team_name, client=client)

    async def async_send_inbox(self, *, session_id: str, payload: dict[str, Any]) -> TransportSendResult:
        subject = self.plan.subject_mapping["inbox"].replace("<session_id>", session_id)
        await self.client.publish(subject, _json_bytes(payload))
        return TransportSendResult(SCHEMA_VERSION, "nats", subject, True)

    def send_inbox(self, *, session_id: str, payload: dict[str, Any]) -> TransportSendResult:
        subject = self.plan.subject_mapping["inbox"].replace("<session_id>", session_id)
        result = self.client.publish(subject, _json_bytes(payload))
        _run_awaitable(result)
        return TransportSendResult(SCHEMA_VERSION, "nats", subject, True)


class A2AHttpAgentTeamTransport:
    """Minimal HTTP JSON adapter for A2A-style agent messages.

    It sends a schema-versioned message envelope to an operator-provided A2A
    endpoint. This keeps default COS dependency-free while making the transport
    executable against any HTTP A2A bridge/gateway.
    """

    def __init__(self, *, team_name: str, endpoint: str, timeout_seconds: float = 5.0) -> None:
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError("endpoint must be http(s)")
        self.team_name = team_name
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.plan = transport_plan(team_name=team_name, backend="a2a")

    def send_inbox(self, *, session_id: str, payload: dict[str, Any]) -> TransportSendResult:
        body = {
            "schema_version": SCHEMA_VERSION,
            "transport": "a2a-http",
            "team_name": self.team_name,
            "recipient": session_id,
            "message_part": payload,
        }
        req = urllib.request.Request(
            self.endpoint,
            data=_json_bytes(body),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:  # noqa: S310 - operator-provided endpoint
            status = getattr(response, "status", 200)
            detail = response.read().decode("utf-8", errors="replace")[-500:]
        return TransportSendResult(SCHEMA_VERSION, "a2a", self.endpoint, 200 <= int(status) < 300, detail)
