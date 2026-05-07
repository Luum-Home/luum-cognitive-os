# SCOPE: both
"""ADR-233 transport upgrade descriptors for agent-team file IPC.

The default transport remains local file IPC.  This module deliberately does not
import NATS/A2A clients; it gives operators and future adapters a machine-
readable migration contract without adding daemons or dependencies.
"""
from __future__ import annotations

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
