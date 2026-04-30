"""End-to-end ADR-081 dispatch tests for Codex live-session payloads."""

from __future__ import annotations

import json
from pathlib import Path

from lib.harness_adapter.dispatch import dispatch_event

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "codex-live-session"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_codex_session_payload_dispatches_to_canonical_stream(tmp_path):
    result = dispatch_event(_fixture("session_meta.json"), project_dir=tmp_path)
    assert result["harness"] == "codex"
    assert result["events"][0]["event_type"] == "session_start"
    canonical = tmp_path / ".cognitive-os" / "metrics" / "canonical-events.jsonl"
    assert canonical.exists()
    rows = _read_jsonl(canonical)
    assert rows[-1]["harness"] == "codex"
    assert rows[-1]["session_id"] == "codex-live-session-001"


def test_codex_tool_payloads_dispatch_without_claude_fallback(tmp_path):
    start = dispatch_event(_fixture("function_call.json"), project_dir=tmp_path)
    end = dispatch_event(_fixture("exec_command_end.json"), project_dir=tmp_path)
    assert start["harness"] == "codex"
    assert end["harness"] == "codex"
    assert start["events"][0]["event_type"] == "tool_use_start"
    assert end["events"][0]["event_type"] == "tool_use_end"
    canonical = tmp_path / ".cognitive-os" / "metrics" / "canonical-events.jsonl"
    event_types = {row["event_type"] for row in _read_jsonl(canonical)}
    assert {"tool_use_start", "tool_use_end"}.issubset(event_types)
