from __future__ import annotations

import pytest

from cos_lib.agent_team_transport import transport_plan


def test_file_transport_is_active_and_losslessly_maps_to_upgrade_targets() -> None:
    plan = transport_plan(team_name="release", backend="file").to_dict()
    assert plan["schema_version"] == "agent-team-transport-plan/v1"
    assert plan["status"] == "active"
    assert plan["compatibility"]["requires_daemon"] is False
    assert plan["compatibility"]["lossless_to"] == ["nats", "a2a"]


def test_nats_and_a2a_are_opt_in_upgrade_targets_without_default_deps() -> None:
    nats = transport_plan(team_name="release", backend="nats").to_dict()
    a2a = transport_plan(team_name="release", backend="a2a").to_dict()
    assert nats["status"] == "upgrade_target"
    assert "opt-in-only" in nats["dependency_policy"]
    assert a2a["subject_mapping"]["handoffs"] == "A2A message part carrying handoff-envelope/v1"
    assert a2a["compatibility"]["conformance"].startswith("none")


def test_transport_plan_rejects_unsafe_team_name() -> None:
    with pytest.raises(ValueError):
        transport_plan(team_name="../bad", backend="file")

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from cos_lib.agent_team_transport import HttpJsonAgentTeamTransport, NatsAgentTeamTransport


class FakeNatsClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, bytes]] = []

    def publish(self, subject: str, payload: bytes) -> None:
        self.published.append((subject, payload))


def test_nats_transport_publishes_to_session_inbox_subject() -> None:
    client = FakeNatsClient()
    result = NatsAgentTeamTransport(team_name="release", client=client).send_inbox(
        session_id="worker",
        payload={"type": "handoff", "id": "h1"},
    )
    assert result.delivered is True
    assert client.published[0][0] == "cos.teams.release.inbox.worker"
    assert json.loads(client.published[0][1])["type"] == "handoff"


def test_http_json_transport_posts_cos_envelope_not_a2a() -> None:
    received: dict[str, object] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers["Content-Length"])
            received.update(json.loads(self.rfile.read(length)))
            self.send_response(202)
            self.end_headers()
            self.wfile.write(b"accepted")

        def log_message(self, *args):  # noqa: ANN001
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        endpoint = f"http://127.0.0.1:{server.server_port}/inbox"
        result = HttpJsonAgentTeamTransport(team_name="release", endpoint=endpoint).send_inbox(
            session_id="worker",
            payload={"type": "handoff", "id": "h1"},
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert result.delivered is True
    assert received["transport"] == "http-json"
    assert received["recipient"] == "worker"
    assert received["message_part"] == {"type": "handoff", "id": "h1"}
    # Guard against the name lying again: this envelope is COS-private, not A2A.
    # A2A Message requires messageId/role/parts and JSON-RPC framing (spec Message).
    assert not {"messageId", "role", "parts", "contextId", "jsonrpc"} & set(received)
    assert result.backend == "http-json"
