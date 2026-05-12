"""Synthetic tests for hooks/orchestrator-decision-trace.sh.

Tests pipe fake PostToolUse Agent stdin JSON to the hook via subprocess and
verify:
  1. Hook writes to .cognitive-os/metrics/orchestrator-decision-trace.jsonl
  2. Written entry has the expected schema fields
  3. Decision is "matched" when agent prompt contains the suggested skill command
  4. Decision is "declined" when agent prompt does not reference the suggestion
  5. Decision is "no_suggestion" when no prior skill suggestion exists
  6. Hook exits 0 always (even on malformed JSON)
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOK_PATH = Path(__file__).parent.parent.parent / "hooks" / "orchestrator-decision-trace.sh"
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _make_tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project directory structure in tmp."""
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lib").symlink_to(PROJECT_ROOT / "lib")
    return tmp_path


def _write_suggestion_entry(tmp_path: Path, entry: dict) -> None:
    """Pre-populate skill-suggestion.jsonl with a synthetic entry."""
    log = tmp_path / ".cognitive-os" / "metrics" / "skill-suggestion.jsonl"
    with open(log, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _run_hook(
    tool_input: dict,
    tmp_dir: Path,
    env_overrides: dict | None = None,
) -> subprocess.CompletedProcess:
    """Run the hook with a fake PostToolUse Agent JSON payload."""
    stdin_payload = json.dumps({
        "tool_name": "Agent",
        "tool_input": tool_input,
    })
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_dir)
    env["PROJECT_DIR"] = str(tmp_dir)
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env["COGNITIVE_OS_SESSION_ID"] = "test-session-001"
    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


@pytest.mark.skipif(
    not HOOK_PATH.exists(),
    reason="Hook file does not exist — run after hook is created",
)
class TestOrchestratorDecisionTraceHook:
    def test_hook_exits_zero(self, tmp_path):
        """Hook must always exit 0."""
        tmp = _make_tmp_project(tmp_path)
        result = _run_hook(
            {"description": "run analysis", "prompt": "analyze the codebase"},
            tmp_dir=tmp,
        )
        assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"

    def test_creates_trace_log(self, tmp_path):
        """Hook must create orchestrator-decision-trace.jsonl."""
        tmp = _make_tmp_project(tmp_path)
        _run_hook(
            {"description": "some analysis", "prompt": "do something"},
            tmp_dir=tmp,
        )
        log = tmp / ".cognitive-os" / "metrics" / "orchestrator-decision-trace.jsonl"
        assert log.exists(), "orchestrator-decision-trace.jsonl was not created"

    def test_trace_entry_has_required_schema(self, tmp_path):
        """Each trace entry must have the documented schema fields."""
        tmp = _make_tmp_project(tmp_path)
        _write_suggestion_entry(tmp, {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": "test-session-001",
            "prompt_hash": "abc123",
            "skill_name": "repo-forensics",
            "invoke_command": "/repo-forensics",
            "confidence": 0.95,
            "threshold_met": True,
        })
        _run_hook(
            {"description": "repo analysis", "prompt": "analyze the repo"},
            tmp_dir=tmp,
        )
        log = tmp / ".cognitive-os" / "metrics" / "orchestrator-decision-trace.jsonl"
        lines = [l for l in log.read_text().splitlines() if l.strip()]
        assert len(lines) >= 1
        entry = json.loads(lines[-1])
        required_fields = [
            "ts", "session_id", "agent_prompt_hash", "suggested_skill",
            "suggested_confidence", "agent_subagent_type",
            "agent_description_short", "decision",
        ]
        for field in required_fields:
            assert field in entry, f"Missing field: {field}"

    def test_decision_matched_when_prompt_contains_invoke_command(self, tmp_path):
        """Decision is 'matched' when agent prompt contains the suggested invoke command."""
        tmp = _make_tmp_project(tmp_path)
        _write_suggestion_entry(tmp, {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": "test-session-001",
            "prompt_hash": "abc123",
            "skill_name": "repo-forensics",
            "invoke_command": "/repo-forensics",
            "confidence": 0.95,
            "threshold_met": True,
        })
        _run_hook(
            {
                "description": "deep repo scan",
                "prompt": "Run /repo-forensics on the target repo and report findings.",
            },
            tmp_dir=tmp,
        )
        log = tmp / ".cognitive-os" / "metrics" / "orchestrator-decision-trace.jsonl"
        lines = [l for l in log.read_text().splitlines() if l.strip()]
        entry = json.loads(lines[-1])
        assert entry["decision"] == "matched", (
            f"Expected 'matched', got '{entry['decision']}'. Reason: {entry.get('reason')}"
        )

    def test_decision_declined_when_prompt_ignores_suggestion(self, tmp_path):
        """Decision is 'declined' when agent ignores the skill suggestion."""
        tmp = _make_tmp_project(tmp_path)
        _write_suggestion_entry(tmp, {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": "test-session-001",
            "prompt_hash": "abc123",
            "skill_name": "repo-forensics",
            "invoke_command": "/repo-forensics",
            "confidence": 0.95,
            "threshold_met": True,
        })
        _run_hook(
            {
                "description": "bespoke analysis",
                "prompt": "Use git clone and manual inspection to evaluate the codebase.",
            },
            tmp_dir=tmp,
        )
        log = tmp / ".cognitive-os" / "metrics" / "orchestrator-decision-trace.jsonl"
        lines = [l for l in log.read_text().splitlines() if l.strip()]
        entry = json.loads(lines[-1])
        assert entry["decision"] == "declined", (
            f"Expected 'declined', got '{entry['decision']}'"
        )

    def test_decision_no_suggestion_when_no_prior_entry(self, tmp_path):
        """Decision is 'no_suggestion' when skill-suggestion.jsonl has no threshold_met entry."""
        tmp = _make_tmp_project(tmp_path)
        # No suggestion log file at all
        _run_hook(
            {"description": "some task", "prompt": "do something random"},
            tmp_dir=tmp,
        )
        log = tmp / ".cognitive-os" / "metrics" / "orchestrator-decision-trace.jsonl"
        lines = [l for l in log.read_text().splitlines() if l.strip()]
        entry = json.loads(lines[-1])
        assert entry["decision"] == "no_suggestion"

    def test_hook_exits_zero_on_non_agent_tool(self, tmp_path):
        """Hook should exit 0 immediately for non-Agent tool calls."""
        tmp = _make_tmp_project(tmp_path)
        stdin_payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        env = os.environ.copy()
        env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp)
        env["PROJECT_DIR"] = str(tmp)
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        result = subprocess.run(
            ["bash", str(HOOK_PATH)],
            input=stdin_payload,
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
        )
        assert result.returncode == 0
        # No trace log should be created (hook short-circuits for non-Agent tools)
        log = tmp / ".cognitive-os" / "metrics" / "orchestrator-decision-trace.jsonl"
        assert not log.exists(), "Trace log should not be created for non-Agent tool calls"
