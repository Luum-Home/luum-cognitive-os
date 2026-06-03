"""End-to-end dispatch tests for OpenCode native plugin payloads."""

from __future__ import annotations

import json
from pathlib import Path

from lib.harness_adapter.dispatch import dispatch_event


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_opencode_lifecycle_payloads_dispatch_to_canonical_stream(tmp_path: Path):
    start = dispatch_event(
        json.dumps({"harness": "opencode", "type": "session.created", "session_id": "oc-1", "cwd": str(tmp_path)}),
        project_dir=tmp_path,
    )
    prompt = dispatch_event(
        json.dumps({"harness": "opencode", "type": "tui.prompt.append", "session_id": "oc-1", "payload": {"prompt": "implement private feature"}}),
        project_dir=tmp_path,
    )
    stop = dispatch_event(
        json.dumps({"harness": "opencode", "type": "session.idle", "session_id": "oc-1"}),
        project_dir=tmp_path,
    )

    assert start["harness"] == "opencode"
    assert prompt["harness"] == "opencode"
    assert stop["harness"] == "opencode"
    records = _read_jsonl(tmp_path / ".cognitive-os" / "metrics" / "canonical-events.jsonl")
    assert [row["event_type"] for row in records] == ["session_start", "user_prompt_submit", "session_end"]
    assert records[1]["prompt_hash"]
    assert records[1]["prompt_summary"] == "implement private feature"


def test_opencode_tool_payloads_dispatch_without_bare_cli_fallback(tmp_path: Path):
    before = dispatch_event(
        json.dumps({"harness": "opencode", "type": "tool.execute.before", "session_id": "oc-2", "tool": "bash", "args": {"command": "echo private"}}),
        project_dir=tmp_path,
    )
    after = dispatch_event(
        json.dumps({"harness": "opencode", "type": "tool.execute.after", "session_id": "oc-2", "tool": "bash", "payload": {"exit_code": 0}}),
        project_dir=tmp_path,
    )

    assert before["harness"] == "opencode"
    assert after["harness"] == "opencode"
    records = _read_jsonl(tmp_path / ".cognitive-os" / "metrics" / "canonical-events.jsonl")
    assert {row["event_type"] for row in records} == {"tool_use_start", "tool_use_end"}
    assert {row["session_id"] for row in records} == {"oc-2"}
    assert all(row["tool_name"] == "bash" for row in records)
