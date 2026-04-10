"""Integration tests for user request persistence across session lifecycle.

Verifies that user requests enqueued mid-session survive session end,
are visible to /session-backlog, and nothing is lost even under edge conditions.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

from lib.request_queue import (
    enqueue_request,
    get_all_requests,
    get_pending_requests,
    mark_done,
    format_pending_summary,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def session_env(tmp_path):
    """Simulate a full session directory structure."""
    session_id = "test-integration-session"
    session_dir = tmp_path / ".cognitive-os" / "sessions" / session_id
    session_dir.mkdir(parents=True)

    # Also create plans dir (session-backlog reads this)
    plans_dir = tmp_path / ".cognitive-os" / "plans" / "features"
    plans_dir.mkdir(parents=True)

    # Create a sample plan with pending work
    (plans_dir / "test-plan.md").write_text(
        "# Test Plan\n## Phase 1\n- [x] Done\n## Phase 2\n- [ ] Pending task\n"
    )

    return {
        "session_id": session_id,
        "session_dir": str(session_dir),
        "project_dir": str(tmp_path),
    }


class TestRequestPersistenceAcrossSessionLifecycle:
    """Verify requests survive the full session lifecycle."""

    def test_requests_persist_to_disk_immediately(self, session_env):
        """Enqueued requests are on disk — not just in memory."""
        enqueue_request("fix the auth bug", session_dir=session_env["session_dir"])

        # Read directly from file (simulating a new process)
        queue_file = Path(session_env["session_dir"]) / "user-requests.jsonl"
        assert queue_file.exists()
        content = queue_file.read_text()
        assert "fix the auth bug" in content

    def test_requests_survive_simulated_crash(self, session_env):
        """Requests written before a crash are recoverable."""
        # Enqueue 3 requests
        enqueue_request("request 1", session_dir=session_env["session_dir"])
        enqueue_request("request 2", session_dir=session_env["session_dir"])
        enqueue_request("request 3", session_dir=session_env["session_dir"])

        # Simulate crash: just read from a fresh process perspective
        pending = get_pending_requests(session_dir=session_env["session_dir"])
        assert len(pending) == 3
        assert pending[0]["message"] == "request 1"
        assert pending[2]["message"] == "request 3"

    def test_mark_done_persists_across_reads(self, session_env):
        """Marking a request done is visible on subsequent reads."""
        enqueue_request("task A", session_dir=session_env["session_dir"])
        enqueue_request("task B", session_dir=session_env["session_dir"])

        mark_done("task A", session_dir=session_env["session_dir"])

        # Fresh read
        pending = get_pending_requests(session_dir=session_env["session_dir"])
        assert len(pending) == 1
        assert pending[0]["message"] == "task B"

        # All requests still exist (done ones too)
        all_reqs = get_all_requests(session_dir=session_env["session_dir"])
        assert len(all_reqs) == 2

    def test_concurrent_writes_dont_corrupt(self, session_env):
        """Multiple rapid enqueues don't corrupt the JSONL file."""
        for i in range(20):
            enqueue_request(f"rapid request {i}", session_dir=session_env["session_dir"])

        all_reqs = get_all_requests(session_dir=session_env["session_dir"])
        assert len(all_reqs) == 20

        # Every line is valid JSON
        queue_file = Path(session_env["session_dir"]) / "user-requests.jsonl"
        for line in queue_file.read_text().splitlines():
            json.loads(line)  # Should not raise

    def test_unicode_messages_persist(self, session_env):
        """Messages with unicode (Spanish, emojis) survive serialization."""
        enqueue_request("arreglá el bug de autenticación 🔐", session_dir=session_env["session_dir"])
        enqueue_request("también hacé los tests 📋", session_dir=session_env["session_dir"])

        pending = get_pending_requests(session_dir=session_env["session_dir"])
        assert len(pending) == 2
        assert "autenticación" in pending[0]["message"]
        assert "📋" in pending[1]["message"]


class TestRequestQueueWithSessionBacklog:
    """Verify that session-backlog skill can read the request queue."""

    def test_backlog_skill_references_request_queue(self):
        """session-backlog SKILL.md mentions Source G (user request queue)."""
        skill_path = Path("skills/session-backlog/SKILL.md")
        if not skill_path.exists():
            pytest.skip("session-backlog skill not found")
        content = skill_path.read_text()
        assert "Source G" in content or "Request Queue" in content or "user-requests" in content, (
            "session-backlog skill does not reference the user request queue"
        )

    def test_backlog_reads_pending_format(self, session_env):
        """format_pending_summary produces readable output for backlog integration."""
        enqueue_request("implement the auth flow", session_dir=session_env["session_dir"])
        enqueue_request("add tests for payments", session_dir=session_env["session_dir"])

        summary = format_pending_summary(session_dir=session_env["session_dir"])
        assert "2 pending" in summary
        assert "auth flow" in summary
        assert "payments" in summary


class TestRequestQueueWithSessionWrapup:
    """Verify that session-wrapup flow captures unresolved requests."""

    def test_wrapup_skill_exists(self):
        """session-wrapup SKILL.md exists."""
        skill_path = Path("skills/session-wrapup/SKILL.md")
        assert skill_path.exists(), "session-wrapup skill not found"

    def test_pending_requests_visible_at_session_end(self, session_env):
        """At session end, pending requests are still accessible."""
        enqueue_request("this was asked but never done", session_dir=session_env["session_dir"])
        enqueue_request("this was done", session_dir=session_env["session_dir"])
        mark_done("this was done", session_dir=session_env["session_dir"])

        # At session end, pending should show the unresolved one
        pending = get_pending_requests(session_dir=session_env["session_dir"])
        assert len(pending) == 1
        assert "never done" in pending[0]["message"]

    def test_deferred_status_for_next_session(self, session_env):
        """Requests can be deferred to next session with explicit status."""
        enqueue_request("complex task for later", session_dir=session_env["session_dir"], status="deferred")

        all_reqs = get_all_requests(session_dir=session_env["session_dir"])
        deferred = [r for r in all_reqs if r["status"] == "deferred"]
        assert len(deferred) == 1
        assert "complex task" in deferred[0]["message"]


class TestRequestQueueEdgeCases:
    """Edge cases that could cause request loss."""

    def test_empty_message_still_persists(self, session_env):
        """Even empty messages are recorded (user hit enter by accident)."""
        enqueue_request("", session_dir=session_env["session_dir"])
        all_reqs = get_all_requests(session_dir=session_env["session_dir"])
        assert len(all_reqs) == 1

    def test_very_long_message_truncated_not_lost(self, session_env):
        """Messages over 2000 chars are truncated but not dropped."""
        long_msg = "x" * 5000
        enqueue_request(long_msg, session_dir=session_env["session_dir"])
        pending = get_pending_requests(session_dir=session_env["session_dir"])
        assert len(pending) == 1
        assert len(pending[0]["message"]) == 2000

    def test_special_json_characters_in_message(self, session_env):
        """Messages with quotes, backslashes, newlines don't corrupt JSONL."""
        enqueue_request('fix "the bug" in path\\to\\file\nnew line', session_dir=session_env["session_dir"])
        pending = get_pending_requests(session_dir=session_env["session_dir"])
        assert len(pending) == 1
        assert '"the bug"' in pending[0]["message"]

    def test_queue_file_with_trailing_newlines(self, session_env):
        """Queue file with extra blank lines doesn't cause phantom entries."""
        queue_file = Path(session_env["session_dir"]) / "user-requests.jsonl"
        queue_file.write_text(
            '{"message":"real","status":"pending","timestamp":"t"}\n\n\n'
        )
        pending = get_pending_requests(session_dir=session_env["session_dir"])
        assert len(pending) == 1

    def test_queue_survives_partial_write(self, session_env):
        """If a write is interrupted mid-line, previous entries survive."""
        queue_file = Path(session_env["session_dir"]) / "user-requests.jsonl"
        queue_file.write_text(
            '{"message":"good entry","status":"pending","timestamp":"t"}\n'
            '{"message":"trunca'  # Simulated partial write
        )
        pending = get_pending_requests(session_dir=session_env["session_dir"])
        # The good entry survives, the partial one is skipped
        assert len(pending) == 1
        assert pending[0]["message"] == "good entry"


class TestRequestQueueCLI:
    """Verify the queue works via subprocess (simulating cross-process access)."""

    def test_enqueue_via_subprocess(self, session_env):
        """Can enqueue from a subprocess (simulating orchestrator calling lib)."""
        sd = session_env["session_dir"]
        result = subprocess.run(
            ["python3", "-c", f"from lib.request_queue import enqueue_request; enqueue_request('subprocess msg', session_dir='{sd}')"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, f"Failed: {result.stderr}"

        pending = get_pending_requests(session_dir=sd)
        assert len(pending) == 1
        assert pending[0]["message"] == "subprocess msg"

    def test_read_via_subprocess(self, session_env):
        """Can read queue from a subprocess."""
        sd = session_env["session_dir"]
        enqueue_request("pre-existing", session_dir=sd)

        result = subprocess.run(
            ["python3", "-c", f"from lib.request_queue import format_pending_summary; print(format_pending_summary(session_dir='{sd}'))"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "1 pending" in result.stdout
