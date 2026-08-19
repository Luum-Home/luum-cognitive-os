# SCOPE: os-only
"""Behavioural test for the decision-depth gate.

Same family of defect as `test_adversarial_review_gate.py`, found the same day:
the gate read `.tool_result`, a field this harness never sends. Claude Code
delivers the Agent result under `.tool_response`, and for the Agent tool that
value is an OBJECT — {status, agentType, content:[{type,text}],
totalDurationMs, totalTokens, totalToolUseCount} — a shape confirmed over 226
real Agent results in the `~/.claude/projects` transcripts (2026-08-19).

Telemetry that motivated the cases: 182 recorded invocations across
`.cognitive-os/metrics/hook-timing.jsonl` plus the rotated archives, and
`.cognitive-os/metrics/decision-depth-gate.jsonl` at exactly 0 bytes since
2026-05-23 — including the `pass` branch, which writes unconditionally.

Covered in both directions:
  * a real Claude Code payload closing a finding with "I'll document this" and
    no investigation MUST warn and log `shallow_resolution`;
  * the same payload WITH the investigation MUST stay silent and log `pass`;
  * a payload with no finding context, and an empty one, MUST leave no trace;
  * the legacy `.tool_result` string shape MUST keep working (Kiro/Devin);
  * every path MUST exit 0 — this is a PostToolUse warning, not a blocker.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_REL = "hooks/decision-depth-gate.sh"
LOG_REL = ".cognitive-os/metrics/decision-depth-gate.jsonl"
WARNING_MARK = "WARNING [decision-depth-gate]"

SHALLOW = (
    "Finding: the two configs diverge on the retry ceiling. "
    "This is intentionally different, so I'll document this difference and move on."
)
INVESTIGATED = (
    "Finding: the two configs diverge on the retry ceiling. I traced it to the "
    "dispatcher, which caps retries at 3 because the queue lease is 3 minutes; "
    "the invariant holds, so I'll document this difference."
)
NO_FINDING = "Implemented the parser and added three unit tests for it."


def _hook_source() -> Path:
    """Where to copy the hook from — overridable only for the falsification run."""
    override = os.environ.get("COS_TEST_HOOK_SOURCE_DIR")
    base = Path(override) if override else REPO_ROOT
    return base / HOOK_REL


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    repo = (tmp_path / "repo").resolve()
    (repo / "hooks").mkdir(parents=True)
    shutil.copy(_hook_source(), repo / HOOK_REL)
    (repo / HOOK_REL).chmod(0o755)
    shutil.copytree(REPO_ROOT / "hooks" / "_lib", repo / "hooks" / "_lib")
    (repo / ".cognitive-os" / "metrics").mkdir(parents=True)
    return repo


def claude_code_payload(text: str) -> dict:
    """The shape Claude Code actually sends on PostToolUse for the Agent tool."""
    return {
        "tool_name": "Agent",
        "tool_input": {"description": "audit the two configs", "subagent_type": "Explore"},
        "tool_response": {
            "status": "completed",
            "agentType": "Explore",
            "content": [{"type": "text", "text": text}],
            "totalDurationMs": 41230,
            "totalTokens": 18422,
            "totalToolUseCount": 9,
        },
    }


def run_hook(repo: Path, payload: dict) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env.pop("DISABLE_HOOK_DECISION_DEPTH_GATE", None)
    return subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo),
        timeout=60,
    )


def log_entries(repo: Path) -> list[dict]:
    path = repo / LOG_REL
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# --- must warn ---------------------------------------------------------------


def test_shallow_resolution_in_a_real_payload_is_warned(repo: Path) -> None:
    """The case the gate exists for, in the payload the harness actually sends.

    If this goes red, the gate is blind in the harness it is registered in —
    which is exactly what 182 silent invocations meant.
    """
    result = run_hook(repo, claude_code_payload(SHALLOW))

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK in result.stdout, (
        f"gate stayed silent on a shallow resolution in a Claude Code payload: {result.stdout!r}"
    )
    entries = log_entries(repo)
    assert entries, "nothing was logged for a Claude Code shaped payload"
    assert entries[-1]["severity"] == "shallow_resolution"
    assert entries[-1]["investigated"] is False


def test_legacy_tool_result_string_still_warns(repo: Path) -> None:
    """Other harnesses (Kiro/Devin shapes) send the output as a plain string."""
    payload = {
        "tool_name": "Agent",
        "tool_input": {"description": "audit the two configs"},
        "tool_result": SHALLOW,
    }
    result = run_hook(repo, payload)

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK in result.stdout
    assert log_entries(repo)


# --- must stay silent --------------------------------------------------------


def test_investigated_resolution_is_not_warned(repo: Path) -> None:
    result = run_hook(repo, claude_code_payload(INVESTIGATED))

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK not in result.stdout, (
        f"gate warned on a finding that WAS traced to root: {result.stdout!r}"
    )
    entries = log_entries(repo)
    assert entries and entries[-1]["severity"] == "pass"
    assert entries[-1]["investigated"] is True


def test_agent_call_without_a_finding_leaves_no_trace(repo: Path) -> None:
    result = run_hook(repo, claude_code_payload(NO_FINDING))

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK not in result.stdout
    assert log_entries(repo) == [], "an agent call with no finding was logged"


def test_empty_response_leaves_no_trace(repo: Path) -> None:
    payload = {"tool_name": "Agent", "tool_input": {"description": "audit"}, "tool_response": ""}
    result = run_hook(repo, payload)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""
    assert log_entries(repo) == []


def test_non_agent_tool_is_ignored(repo: Path) -> None:
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "git status"},
        "tool_response": {"content": [{"type": "text", "text": SHALLOW}]},
    }
    result = run_hook(repo, payload)

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK not in result.stdout
    assert log_entries(repo) == []


# --- must never block --------------------------------------------------------


@pytest.mark.parametrize("text", [SHALLOW, INVESTIGATED, NO_FINDING, ""])
def test_gate_never_blocks(repo: Path, text: str) -> None:
    result = run_hook(repo, claude_code_payload(text))
    assert result.returncode == 0, (
        f"the gate blocked — it is a PostToolUse warning, not a stop: {result.stderr}"
    )


def test_log_is_one_json_object_per_line(repo: Path) -> None:
    """`safe_jsonl_append` takes ONE line; pretty JSON makes the ledger unreadable."""
    run_hook(repo, claude_code_payload(SHALLOW))
    run_hook(repo, claude_code_payload(INVESTIGATED))

    lines = (repo / LOG_REL).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2, f"two events wrote {len(lines)} lines: {lines!r}"
    for line in lines:
        json.loads(line)
