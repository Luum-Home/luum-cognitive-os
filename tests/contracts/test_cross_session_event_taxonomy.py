from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from cos_lib.agent_message_bus import ack_message, send_message
from cos_lib.branch_lock import acquire, release
from cos_lib.session_bus import SESSION_EVENT_TAXONOMY, read_events

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
EVENT_HOOK = REPO / "hooks" / "cross-session-event-emit.sh"
SETTINGS_DRIVER = REPO / "scripts" / "_lib" / "settings-driver-claude-code.sh"

EXPECTED_V1_EVENTS = {
    "session-start",
    "branch-acquire",
    "branch-release",
    "coordination-claim",
    "worktree-intake",
    "agent-message-sent",
    "agent-message-ack",
    "agent-spawn",
    "file-write-intent",
    "commit-intent",
    "commit-landed",
    "session-end",
}


def run_event_hook(tmp_path: Path, payload: dict[str, object], *, session_id: str = "s-hook") -> None:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": session_id}
    res = subprocess.run(
        ["bash", str(EVENT_HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )
    assert res.returncode == 0, res.stderr


def test_adr_183_v1_taxonomy_is_pinned_but_open() -> None:
    assert EXPECTED_V1_EVENTS.issubset(SESSION_EVENT_TAXONOMY)


@pytest.mark.parametrize(
    ("payload", "event_type"),
    [
        ({"hook_event_name": "SessionStart"}, "session-start"),
        ({"hook_event_name": "Stop"}, "session-end"),
        ({"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": {"prompt": "review ADR routing"}}, "agent-spawn"),
        ({"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": "docs/x.md"}}, "file-write-intent"),
        ({"hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": {"file_path": "cos_lib/x.py"}}, "file-write-intent"),
        ({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}, "commit-intent"),
        ({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}, "commit-landed"),
    ],
)
def test_cross_session_emit_hook_maps_core_lifecycle_events(tmp_path: Path, payload: dict[str, object], event_type: str) -> None:
    run_event_hook(tmp_path, payload)
    events = read_events(project_dir=tmp_path, event_type=event_type)
    assert events, f"missing emitted {event_type}"


def test_branch_and_agent_message_producers_emit_taxonomy_events(tmp_path: Path) -> None:
    assert acquire(tmp_path, branch="session/test", session_id="writer", pid=os.getpid(), worktree=tmp_path)["status"] == "acquired"
    assert release(tmp_path, branch="session/test", session_id="writer") is True

    message = send_message(
        tmp_path,
        from_session="auditor",
        to_session="writer",
        message_type="audit_finding",
        severity="warn",
        body="review before commit",
    )
    ack_message(tmp_path, message_id_value=message["message_id"], session_id="writer", status="seen")

    event_types = {row["event_type"] for row in read_events(project_dir=tmp_path)}
    assert {"branch-acquire", "branch-release", "agent-message-sent", "agent-message-ack"}.issubset(event_types)


def test_settings_driver_wires_event_emitters_and_context_hooks() -> None:
    text = SETTINGS_DRIVER.read_text(encoding="utf-8")

    assert '"hooks/cross-session-event-emit.sh"       "true"' in text  # SessionStart/core path
    assert '"hooks/cross-session-event-emit.sh"      "true"' in text  # PreToolUse Write/Edit and Agent paths
    assert '"hooks/cross-session-event-emit.sh"     "true"' in text  # PostToolUse Bash path
    assert '"hooks/cross-session-event-emit.sh"        "true"' in text  # Stop path
    # Presencia, NO valor de async. Este test se llama "wires ... context hooks":
    # su trabajo es que el driver los cablee, no que politica de async llevan.
    #
    # Hasta 2026-08-19 asertaba "true" sobre estos dos, y eso lo convirtio en
    # DEFENSOR DE UN DEFECTO: async en UserPromptSubmit entrega el contexto en el
    # turno siguiente, desacoplado del prompt que lo motivo, y estos dos hooks
    # existen justamente para avisar EN el turno (sesiones pares en conflicto,
    # mensajes dirigidos entre agentes). Al corregirse el async a false, este test
    # se puso rojo defendiendo el bug -- tercer caso del mismo dia, despues de dos
    # `assert ... == ""` que defendian el descarte silencioso de payloads.
    #
    # La asercion sobre async vive ahora donde corresponde, y sobre los CUATRO
    # moldes del settings en vez de solo sobre este driver:
    # tests/contracts/test_hook_header_registration_claims.py
    assert '"hooks/cross-session-peer-context.sh"' in text
    assert '"hooks/agent-message-inbox-context.sh"' in text
