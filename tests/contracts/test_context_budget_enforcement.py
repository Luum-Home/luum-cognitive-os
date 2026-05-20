from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from lib.agent_message_bus import send_message
from lib.session_bus import append_event

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
METER = REPO / "hooks" / "context-budget-meter.sh"
PEER = REPO / "hooks" / "cross-session-peer-context.sh"
INBOX = REPO / "hooks" / "agent-message-inbox-context.sh"


def test_user_prompt_meter_always_writes_metric(tmp_path: Path) -> None:
    payload = {"prompt": "hello context budget"}
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s1"}
    res = subprocess.run(["bash", str(METER)], input=json.dumps(payload), text=True, capture_output=True, env=env, timeout=10)
    assert res.returncode == 0
    log = tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl"
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert rows[-1]["source"] == "context-budget-meter"
    assert rows[-1]["verdict"] == "PASS"

    resource_log = tmp_path / ".cognitive-os" / "metrics" / "ai-resource-ledger.jsonl"
    resource_rows = [json.loads(line) for line in resource_log.read_text().splitlines()]
    assert resource_rows[-1]["schema_version"] == 1
    assert resource_rows[-1]["source"] == "context-budget-meter"
    assert resource_rows[-1]["kind"] == "context_budget"
    assert resource_rows[-1]["session_id"] == "s1"
    assert resource_rows[-1]["tokens_in"] == rows[-1]["tokens_estimate"]
    assert resource_rows[-1]["tokens_out"] == 0
    assert resource_rows[-1]["actual_cost_usd"] == 0.0
    assert resource_rows[-1]["tool_calls"] == 0


def test_meter_blocks_large_user_context_without_override(tmp_path: Path) -> None:
    (tmp_path / "cognitive-os.yaml").write_text("context_budget:\n  user_max_tokens: 1\n", encoding="utf-8")
    payload = {"prompt": "x" * 20}
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s1"}
    res = subprocess.run(["bash", str(METER)], input=json.dumps(payload), text=True, capture_output=True, env=env, timeout=10)
    assert res.returncode == 2
    assert "context-budget-meter: BLOCK" in res.stderr


def test_accounted_context_hook_logs_before_emitting(tmp_path: Path) -> None:
    append_event("file-write-intent", {"branch": "session/a", "path": "docs/02-Decisions/adrs/ADR-1.md"}, project_dir=tmp_path, session_id="peer")
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "me"}
    res = subprocess.run(["bash", str(PEER)], text=True, capture_output=True, env=env, timeout=10)
    assert res.returncode == 0
    assert "additionalContext" in res.stdout
    log = tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl"
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert rows[-1]["source"] == "cross-session-peer-context"


def test_accounted_context_hook_skips_when_static_budget_blocks(tmp_path: Path) -> None:
    (tmp_path / "cognitive-os.yaml").write_text("context_budget:\n  static_max_tokens: 1\n", encoding="utf-8")
    send_message(tmp_path, from_session="auditor", to_session="me", message_type="audit_finding", severity="warn", body="x" * 100)
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "me"}
    res = subprocess.run(["bash", str(INBOX)], text=True, capture_output=True, env=env, timeout=10)
    assert res.returncode == 0
    assert res.stdout.strip() == ""
    log = tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl"
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert rows[-1]["verdict"] == "BLOCK"


def test_meter_block_override_allows_and_logs_override(tmp_path: Path) -> None:
    (tmp_path / "cognitive-os.yaml").write_text("context_budget:\n  user_max_tokens: 1\n", encoding="utf-8")
    payload = {"prompt": "x" * 20}
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COGNITIVE_OS_SESSION_ID": "s1",
        "COS_ALLOW_CONTEXT_BUDGET_OVERRUN": "1",
    }
    res = subprocess.run(["bash", str(METER)], input=json.dumps(payload), text=True, capture_output=True, env=env, timeout=10)
    assert res.returncode == 0
    row = json.loads((tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl").read_text().splitlines()[-1])
    assert row["verdict"] == "BLOCK"
    assert row["allowed"] is True
    assert row["reason"] == "override"


def test_meter_warns_without_blocking(tmp_path: Path) -> None:
    (tmp_path / "cognitive-os.yaml").write_text("context_budget:\n  user_max_tokens: 10\n", encoding="utf-8")
    payload = {"prompt": "x" * 44}  # 11 heuristic tokens -> 1.1x
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s1"}
    res = subprocess.run(["bash", str(METER)], input=json.dumps(payload), text=True, capture_output=True, env=env, timeout=10)
    assert res.returncode == 0
    assert "context-budget-meter: WARN" in res.stderr
    row = json.loads((tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl").read_text().splitlines()[-1])
    assert row["verdict"] == "WARN"
    assert row["latency_ms"] >= 0


def test_meter_handles_empty_or_malformed_input_and_still_logs(tmp_path: Path) -> None:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s1"}
    res = subprocess.run(["bash", str(METER)], input="not-json", text=True, capture_output=True, env=env, timeout=10)
    assert res.returncode == 0
    row = json.loads((tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl").read_text().splitlines()[-1])
    assert row["source"] == "context-budget-meter"
    assert row["total_chars"] == 0
