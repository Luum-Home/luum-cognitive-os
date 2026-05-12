from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from lib.session_bus import append_event, peers, read_events

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
EVENT_HOOK = REPO / "hooks" / "cross-session-event-emit.sh"
PEER_HOOK = REPO / "hooks" / "cross-session-peer-context.sh"


def test_append_event_standardizes_schema_and_reads_by_type(tmp_path: Path) -> None:
    row = append_event("file_write_intent", {"path": "docs/02-Decisions/adrs/ADR-183.md"}, project_dir=tmp_path, session_id="s1")

    assert row["schema_version"] == 1
    assert row["event_type"] == "file-write-intent"
    assert read_events(project_dir=tmp_path, event_type="file-write-intent")[0]["payload"]["path"] == "docs/02-Decisions/adrs/ADR-183.md"


def test_peers_summarizes_recent_live_peer(tmp_path: Path) -> None:
    append_event("session-start", {"branch": "session/a", "topic_keywords": ["routing"]}, project_dir=tmp_path, session_id="peer")
    append_event("file-write-intent", {"branch": "session/a", "path": "lib/session_bus.py"}, project_dir=tmp_path, session_id="peer")

    result = peers(project_dir=tmp_path, current_session_id="me", alive_only=True)

    assert result
    assert result[0].session_id == "peer"
    assert result[0].recent_writes == ["lib/session_bus.py"]


def test_event_emit_hook_maps_write_payload(tmp_path: Path) -> None:
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": "docs/x.md"}}
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s-hook"}
    res = subprocess.run(["bash", str(EVENT_HOOK)], input=json.dumps(payload), text=True, capture_output=True, env=env, timeout=10)

    assert res.returncode == 0
    events = read_events(project_dir=tmp_path, event_type="file-write-intent")
    assert events[0]["payload"]["path"] == "docs/x.md"


def test_peer_context_hook_emits_additional_context_for_peer(tmp_path: Path) -> None:
    append_event("file-write-intent", {"branch": "session/peer", "path": "docs/02-Decisions/adrs/ADR-171.md", "topic_keywords": ["adr"]}, project_dir=tmp_path, session_id="peer")
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "me"}
    res = subprocess.run(["bash", str(PEER_HOOK)], text=True, capture_output=True, env=env, timeout=10)

    assert res.returncode == 0
    out = json.loads(res.stdout)
    assert "Peer orchestrator sessions detected" in out["additionalContext"]
    assert "docs/02-Decisions/adrs/ADR-171.md" in out["additionalContext"]
