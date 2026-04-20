"""Behavior tests for agent resilience against runaway tool-call loops.

Context: A sub-agent ran 476 tool calls, exhausted the parent's context,
triggered compaction, and killed the main conversation thread. These tests
verify the safety nets that prevent this class of failure.

Tests check what IS (existing infrastructure) and mark missing features as
xfail so the suite stays green while WS14 implements the missing pieces.
"""

import ast
import inspect
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
HOOKS_DIR = PROJECT_ROOT / "hooks"
LIB_DIR = PROJECT_ROOT / "lib"
SETTINGS_PATH = PROJECT_ROOT / ".claude" / "settings.json"
PREAMBLE_PATH = TEMPLATES_DIR / "agent-preamble.md"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def preamble_content() -> str:
    assert PREAMBLE_PATH.exists(), f"agent-preamble.md not found at {PREAMBLE_PATH}"
    return PREAMBLE_PATH.read_text()


@pytest.fixture(scope="module")
def settings_hooks() -> dict:
    """Return the hooks section of .claude/settings.json."""
    if not SETTINGS_PATH.exists():
        return {}
    d = json.loads(SETTINGS_PATH.read_text())
    return d.get("hooks", {})


@pytest.fixture(scope="module")
def all_registered_commands(settings_hooks) -> list[str]:
    """Flat list of all hook commands registered in settings.json."""
    cmds = []
    for hook_type, entries in settings_hooks.items():
        if isinstance(entries, list):
            for entry in entries:
                # Handle both array-of-objects and array-of-arrays
                if isinstance(entry, dict):
                    for h in entry.get("hooks", []):
                        if isinstance(h, dict):
                            cmd = h.get("command", "")
                            if cmd:
                                cmds.append(cmd)
                elif isinstance(entry, str):
                    cmds.append(entry)
    return cmds


# ===========================================================================
# A. Tool-Call Budget Tests
# ===========================================================================


class TestToolCallBudget:
    """Verify the preamble instructs agents on tool-call limits."""

    def test_preamble_has_explicit_tool_call_limit(self, preamble_content):
        """Preamble must state a concrete numeric cap (e.g., 'max 50 tool calls').

        Without a hard number, agents have no budget to self-monitor against.
        The 476-tool-call incident happened because there was no explicit ceiling.
        Referencing '80% of expected budget' is insufficient when the budget
        itself is never defined.
        """
        import re
        # Look for a concrete number tied to tool calls, e.g.:
        # "max 50 tool calls", "100-tool-call limit", "budget: 75 tool calls"
        has_concrete_numeric_ceiling = bool(
            re.search(
                r"\b(max|limit|cap|budget)[:\s]+\d+\s*tool.calls?\b"
                r"|\b\d+\s*tool.calls?\s*(max|limit|cap|budget|ceiling)\b"
                r"|\btool.call\s*(budget|limit|cap|ceiling)\s*[:=]\s*\d+\b",
                preamble_content,
                re.IGNORECASE,
            )
        )
        assert has_concrete_numeric_ceiling, (
            "Preamble must specify a concrete numeric tool-call budget "
            "(e.g., 'max 50 tool calls per task'). "
            "Currently it says '>80% of expected budget' without defining what "
            "the expected budget IS, giving agents nothing concrete to self-monitor against."
        )


    def test_preamble_has_save_and_stop_for_budget_exhaustion(self, preamble_content):
        """Preamble must instruct agents to save progress and stop on budget exhaustion."""
        lower = preamble_content.lower()
        has_save_partial = (
            "save partial" in lower
            or "save any" in lower
            or "save progress" in lower
            or ("save" in lower and "escalat" in lower)
        )
        assert has_save_partial, (
            "Preamble must instruct agents to save partial progress to Engram "
            "before escalating when budget is exhausted. "
            "Found no 'save partial progress' or equivalent instruction."
        )


# ===========================================================================
# B. Compaction Resilience Tests
# ===========================================================================


class TestCompactionResilience:
    """Verify the compaction protection hook exists and is wired correctly."""


    def test_pre_compaction_flush_is_syntactically_valid(self):
        """pre-compaction-flush.sh must pass bash -n syntax check."""
        flush_hook = HOOKS_DIR / "pre-compaction-flush.sh"
        if not flush_hook.exists():
            pytest.skip("pre-compaction-flush.sh not found")
        result = subprocess.run(
            ["bash", "-n", str(flush_hook)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"pre-compaction-flush.sh has syntax errors:\n{result.stderr}"
        )

    def test_pre_compaction_flush_mentions_engram_save(self):
        """pre-compaction-flush.sh must instruct the agent to save to Engram."""
        flush_hook = HOOKS_DIR / "pre-compaction-flush.sh"
        if not flush_hook.exists():
            pytest.skip("pre-compaction-flush.sh not found")
        content = flush_hook.read_text().lower()
        has_engram_save = (
            "mem_save" in content
            or "mem_session_summary" in content
            or "engram" in content
        )
        assert has_engram_save, (
            "pre-compaction-flush.sh must instruct the agent to call mem_save or "
            "mem_session_summary before compaction destroys working memory."
        )

    def test_pre_compaction_flush_registered_in_settings(self, all_registered_commands):
        """pre-compaction-flush.sh must be registered as a hook in settings.json."""
        is_registered = any(
            "pre-compaction-flush" in cmd for cmd in all_registered_commands
        )
        assert is_registered, (
            "pre-compaction-flush.sh is not registered in .claude/settings.json. "
            "The hook file exists but won't fire unless registered. "
            "Add it under a PreCompact (or equivalent) hook type."
        )


    def test_crash_recovery_registered_in_settings(self, all_registered_commands):
        """crash-recovery.sh must be registered in settings.json SessionStart hooks."""
        is_registered = any(
            "crash-recovery" in cmd for cmd in all_registered_commands
        )
        assert is_registered, (
            "crash-recovery.sh is not registered in .claude/settings.json. "
            "It must be a SessionStart hook to detect prior unclean shutdowns."
        )

    def test_session_init_registered_in_settings(self, all_registered_commands):
        """session-init.sh must be registered in settings.json SessionStart hooks."""
        is_registered = any(
            "session-init" in cmd for cmd in all_registered_commands
        )
        assert is_registered, (
            "session-init.sh is not registered in .claude/settings.json. "
            "It must run at SessionStart to create isolated session directories."
        )


# ===========================================================================
# C. Request Persistence Tests
# ===========================================================================


class TestRequestPersistence:
    """Verify that user requests survive context compaction via the queue file."""


    def test_request_queue_has_enqueue_function(self):
        """lib/request_queue.py must export enqueue_request."""
        sys.path.insert(0, str(LIB_DIR))
        try:
            import request_queue
            assert hasattr(request_queue, "enqueue_request"), (
                "request_queue.enqueue_request function not found. "
                "The orchestrator calls this to persist user messages."
            )
        finally:
            if "request_queue" in sys.modules:
                del sys.modules["request_queue"]
            sys.path.pop(0)

    def test_request_queue_has_mark_done_function(self):
        """lib/request_queue.py must export mark_done."""
        sys.path.insert(0, str(LIB_DIR))
        try:
            import request_queue
            assert hasattr(request_queue, "mark_done"), (
                "request_queue.mark_done function not found. "
                "The orchestrator calls this to record completed requests."
            )
        finally:
            if "request_queue" in sys.modules:
                del sys.modules["request_queue"]
            sys.path.pop(0)

    def test_enqueue_request_writes_to_disk(self, tmp_path):
        """enqueue_request must write to a file (not just memory)."""
        sys.path.insert(0, str(LIB_DIR))
        try:
            import request_queue
            session_dir = str(tmp_path / "session")
            request_queue.enqueue_request("test message", session_dir=session_dir)
            queue_file = tmp_path / "session" / "user-requests.jsonl"
            assert queue_file.exists(), (
                "enqueue_request did not create a file on disk. "
                "The queue must be file-based so it survives context compaction."
            )
            content = queue_file.read_text().strip()
            assert len(content) > 0, "Queue file is empty after enqueue_request"
        finally:
            if "request_queue" in sys.modules:
                del sys.modules["request_queue"]
            sys.path.pop(0)

    def test_enqueue_request_stores_message_text(self, tmp_path):
        """enqueue_request must store the message text in the queue file."""
        sys.path.insert(0, str(LIB_DIR))
        try:
            import request_queue
            session_dir = str(tmp_path / "session")
            test_message = "implement the payment feature"
            request_queue.enqueue_request(test_message, session_dir=session_dir)
            queue_file = tmp_path / "session" / "user-requests.jsonl"
            entry = json.loads(queue_file.read_text().strip())
            assert entry.get("message") == test_message, (
                f"Expected message '{test_message}' in queue entry, got: {entry}"
            )
        finally:
            if "request_queue" in sys.modules:
                del sys.modules["request_queue"]
            sys.path.pop(0)

    def test_requests_survive_across_calls(self, tmp_path):
        """Multiple enqueue_request calls must accumulate in the file."""
        sys.path.insert(0, str(LIB_DIR))
        try:
            import request_queue
            session_dir = str(tmp_path / "session")
            request_queue.enqueue_request("first request", session_dir=session_dir)
            request_queue.enqueue_request("second request", session_dir=session_dir)
            request_queue.enqueue_request("third request", session_dir=session_dir)
            queue_file = tmp_path / "session" / "user-requests.jsonl"
            lines = [l for l in queue_file.read_text().splitlines() if l.strip()]
            assert len(lines) == 3, (
                f"Expected 3 entries in queue file, got {len(lines)}. "
                "Requests must accumulate across calls, not overwrite."
            )
        finally:
            if "request_queue" in sys.modules:
                del sys.modules["request_queue"]
            sys.path.pop(0)

    def test_mark_done_updates_status(self, tmp_path):
        """mark_done must change the status of a pending request."""
        sys.path.insert(0, str(LIB_DIR))
        try:
            import request_queue
            session_dir = str(tmp_path / "session")
            request_queue.enqueue_request("implement login feature", session_dir=session_dir)
            result = request_queue.mark_done("implement login", session_dir=session_dir)
            assert result is True, (
                "mark_done returned False — it should return True when a matching request is found."
            )
            # Verify status changed in file
            queue_file = tmp_path / "session" / "user-requests.jsonl"
            entry = json.loads(queue_file.read_text().strip())
            assert entry.get("status") == "done", (
                f"Expected status 'done' after mark_done, got: {entry.get('status')}"
            )
        finally:
            if "request_queue" in sys.modules:
                del sys.modules["request_queue"]
            sys.path.pop(0)

    def test_get_pending_requests_excludes_done(self, tmp_path):
        """get_pending_requests must only return entries with status 'pending'."""
        sys.path.insert(0, str(LIB_DIR))
        try:
            import request_queue
            session_dir = str(tmp_path / "session")
            request_queue.enqueue_request("pending task", session_dir=session_dir)
            request_queue.enqueue_request("completed task", session_dir=session_dir)
            request_queue.mark_done("completed task", session_dir=session_dir)
            pending = request_queue.get_pending_requests(session_dir=session_dir)
            assert len(pending) == 1, (
                f"Expected 1 pending request, got {len(pending)}. "
                "get_pending_requests must exclude 'done' entries."
            )
            assert pending[0]["message"] == "pending task"
        finally:
            if "request_queue" in sys.modules:
                del sys.modules["request_queue"]
            sys.path.pop(0)


# ===========================================================================
# D. Background Agent Isolation Tests
# ===========================================================================


class TestBackgroundAgentIsolation:
    """Verify preamble documents background execution and Engram save before exit."""


    def test_preamble_instructs_engram_save_before_finish(self, preamble_content):
        """Preamble must instruct agents to save findings to Engram before finishing."""
        lower = preamble_content.lower()
        has_save_instruction = (
            "mem_save" in lower
            or ("save" in lower and "engram" in lower)
            or ("save" in lower and "memory" in lower and "finish" in lower)
        )
        assert has_save_instruction, (
            "Preamble must instruct agents to call mem_save with their findings "
            "before finishing. Without this, compaction destroys all in-session "
            "discoveries and the next agent starts from scratch."
        )


    def test_preamble_warns_against_unrestricted_sub_agent_spawning(self, preamble_content):
        """Preamble must warn agents not to spawn unlimited sub-agents.

        A sub-agent that spawns its own sub-agents without checking slot limits
        can exhaust context across all levels simultaneously.
        """
        lower = preamble_content.lower()
        has_sub_agent_warning = any(
            phrase in lower
            for phrase in [
                "dispatch-gate", "slot limit", "max parallel", "agent slot",
                "do not spawn", "avoid spawning", "check before spawning",
            ]
        )
        assert has_sub_agent_warning, (
            "Preamble must warn agents not to spawn sub-agents without checking "
            "slot availability (dispatch-gate). Unrestricted sub-agent spawning "
            "causes cascading context exhaustion."
        )


# ===========================================================================
# E. State Recovery Tests
# ===========================================================================


class TestStateRecovery:
    """Verify the session and task tracking infrastructure for state recovery."""


    def test_crash_recovery_hook_is_syntactically_valid(self):
        """crash-recovery.sh must pass bash -n syntax check."""
        crash_hook = HOOKS_DIR / "crash-recovery.sh"
        if not crash_hook.exists():
            pytest.skip("crash-recovery.sh not found")
        result = subprocess.run(
            ["bash", "-n", str(crash_hook)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"crash-recovery.sh has syntax errors:\n{result.stderr}"
        )

    def test_session_init_is_syntactically_valid(self):
        """session-init.sh must pass bash -n syntax check."""
        session_init = HOOKS_DIR / "session-init.sh"
        if not session_init.exists():
            pytest.skip("session-init.sh not found")
        result = subprocess.run(
            ["bash", "-n", str(session_init)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"session-init.sh has syntax errors:\n{result.stderr}"
        )


    def test_session_resume_registered_in_settings(self, all_registered_commands):
        """session-resume.sh must be registered as a SessionStart hook."""
        is_registered = any(
            "session-resume" in cmd for cmd in all_registered_commands
        )
        assert is_registered, (
            "session-resume.sh is not registered in .claude/settings.json. "
            "Without registration, it never runs and prior in-progress tasks "
            "are silently abandoned after a crash."
        )
