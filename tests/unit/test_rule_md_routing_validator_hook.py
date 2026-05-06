"""Synthetic tests for hooks/rule-md-routing-validator.sh (ADR-179).

Pipes fake PostToolUse Write JSON to the hook and verifies:
  1. Missing enforcement field -> warning + log entry status=missing-enforcement.
  2. enforcement: agent-instruction without routing_patterns -> warning + log.
  3. enforcement: hook with backing hooks/<name>.sh -> ok status, no warning.
  4. enforcement: hook without backing hook -> warning status=stale-hook-reference.
  5. Files outside rules/ are ignored.
  6. Hook exits 0 in every case (non-blocking).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOK_PATH = (
    Path(__file__).resolve().parents[2] / "hooks" / "rule-md-routing-validator.sh"
)


def _run(payload: dict, project_dir: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["DISABLE_HOOK_RULE_MD_ROUTING_VALIDATOR"] = "0"
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


def _write_rule(project_dir: Path, name: str, content: str) -> Path:
    rules_dir = project_dir / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    path = rules_dir / f"{name}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _read_log(project_dir: Path) -> list[dict]:
    log_file = project_dir / ".cognitive-os" / "metrics" / "rule-md-routing-validator.jsonl"
    if not log_file.is_file():
        return []
    return [json.loads(line) for line in log_file.read_text().splitlines() if line.strip()]


def test_missing_enforcement_warns(tmp_path: Path):
    rule_path = _write_rule(
        tmp_path,
        "no-enforcement",
        "---\ntrigger_priority: high\n---\n# body\n",
    )
    res = _run({"tool_input": {"file_path": str(rule_path)}}, tmp_path)
    assert res.returncode == 0
    assert "rule-md-routing-validator" in res.stderr
    log = _read_log(tmp_path)
    assert any(
        e["rule"] == "no-enforcement" and e["status"] == "missing-enforcement"
        for e in log
    )


def test_agent_instruction_without_routing_patterns_warns(tmp_path: Path):
    rule_path = _write_rule(
        tmp_path,
        "agent-no-patterns",
        "---\nenforcement: agent-instruction\n---\n# body\n",
    )
    res = _run({"tool_input": {"file_path": str(rule_path)}}, tmp_path)
    assert res.returncode == 0
    log = _read_log(tmp_path)
    assert any(
        e["rule"] == "agent-no-patterns"
        and e["status"] == "missing-routing-patterns"
        for e in log
    )


def test_hook_enforcement_with_backing_hook_ok(tmp_path: Path):
    # Create the backing hook so cross-check passes.
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (hooks_dir / "real-hook.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
    rule_path = _write_rule(
        tmp_path,
        "real-hook",
        "---\nenforcement: hook\n---\n# body\n",
    )
    res = _run({"tool_input": {"file_path": str(rule_path)}}, tmp_path)
    assert res.returncode == 0
    log = _read_log(tmp_path)
    statuses = {e["status"] for e in log if e["rule"] == "real-hook"}
    assert statuses == {"ok"}, statuses


def test_hook_enforcement_without_backing_hook_warns(tmp_path: Path):
    rule_path = _write_rule(
        tmp_path,
        "ghost-hook",
        "---\nenforcement: hook\n---\n# body\n",
    )
    res = _run({"tool_input": {"file_path": str(rule_path)}}, tmp_path)
    assert res.returncode == 0
    log = _read_log(tmp_path)
    assert any(
        e["rule"] == "ghost-hook" and e["status"] == "stale-hook-reference"
        for e in log
    )


def test_non_rule_file_ignored(tmp_path: Path):
    other = tmp_path / "README.md"
    other.write_text("nope\n")
    res = _run({"tool_input": {"file_path": str(other)}}, tmp_path)
    assert res.returncode == 0
    # No log entries because hook bailed before instrumentation.
    assert _read_log(tmp_path) == []


def test_killswitch_disables_hook(tmp_path: Path):
    rule_path = _write_rule(
        tmp_path,
        "no-enforcement",
        "---\ntrigger_priority: high\n---\n# body\n",
    )
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    env["DISABLE_HOOK_RULE_MD_ROUTING_VALIDATOR"] = "1"
    res = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps({"tool_input": {"file_path": str(rule_path)}}),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert res.returncode == 0
    assert _read_log(tmp_path) == []
