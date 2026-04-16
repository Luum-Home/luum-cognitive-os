"""Behavior tests for Paperclip integration completeness.

Validates that all 8 Paperclip integration gaps are wired:
- Gap 1: SDD Pipeline Sync hook exists and handles input
- Gap 2: Agent Heartbeat hook exists and handles input
- Gap 3: Singularity event notification wiring exists
- Gap 4: Squad Org Chart sync hook exists
- Gap 5-7: Documented integration points
- Gap 8: Client retry queue logic

Author: luum
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Gap 1: SDD Pipeline Sync
# ---------------------------------------------------------------------------


class TestGap1SDDPipelineSync:
    """Gap 1: SDD phase transitions push to Paperclip."""


    def test_paperclip_sdd_sync_hook_is_executable(self):
        hook = PROJECT_ROOT / "packages" / "paperclip-integration" / "hooks" / "paperclip-sdd-sync.sh"
        assert os.access(hook, os.X_OK), "paperclip-sdd-sync.sh must be executable"

    def test_hook_handles_empty_stdin(self):
        """Hook should exit cleanly with empty stdin."""
        hook = PROJECT_ROOT / "packages" / "paperclip-integration" / "hooks" / "paperclip-sdd-sync.sh"
        result = subprocess.run(
            ["bash", str(hook)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "COGNITIVE_OS_HOOK_HEARTBEAT": "false"},
        )
        assert result.returncode == 0, f"Hook should exit 0 on empty input, got {result.returncode}: {result.stderr}"

    def test_hook_handles_non_agent_tool(self):
        """Hook should exit cleanly when tool_name is not Agent."""
        hook = PROJECT_ROOT / "packages" / "paperclip-integration" / "hooks" / "paperclip-sdd-sync.sh"
        payload = json.dumps({"tool_name": "Bash", "tool_response": "hello"})
        result = subprocess.run(
            ["bash", str(hook)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "COGNITIVE_OS_HOOK_HEARTBEAT": "false"},
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Gap 2: Agent Heartbeat Integration
# ---------------------------------------------------------------------------


class TestGap2AgentHeartbeat:
    """Gap 2: Agent completion pushes status to Paperclip."""


    def test_paperclip_agent_status_hook_is_executable(self):
        hook = PROJECT_ROOT / "packages" / "paperclip-integration" / "hooks" / "paperclip-agent-status.sh"
        assert os.access(hook, os.X_OK), "paperclip-agent-status.sh must be executable"

    def test_hook_handles_empty_stdin(self):
        hook = PROJECT_ROOT / "packages" / "paperclip-integration" / "hooks" / "paperclip-agent-status.sh"
        result = subprocess.run(
            ["bash", str(hook)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "COGNITIVE_OS_HOOK_HEARTBEAT": "false"},
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Gap 3: Singularity Event Notifications
# ---------------------------------------------------------------------------


class TestGap3SingularityEvents:
    """Gap 3: Singularity pushes events to Paperclip inbox."""


    def test_singularity_calls_push_in_record_knowledge(self):
        """record_knowledge should invoke the paperclip push."""
        singularity_path = PROJECT_ROOT / "lib" / "singularity.py"
        content = singularity_path.read_text()
        # Find the record_knowledge function and verify it calls the push
        idx_record = content.find("def record_knowledge")
        assert idx_record > 0
        idx_push = content.find("_push_singularity_to_paperclip", idx_record)
        assert idx_push > idx_record, (
            "record_knowledge must call _push_singularity_to_paperclip"
        )

    def test_push_function_uses_push_notification(self):
        """The push function should call client.push_notification."""
        singularity_path = PROJECT_ROOT / "lib" / "singularity.py"
        content = singularity_path.read_text()
        idx_fn = content.find("def _push_singularity_to_paperclip")
        assert idx_fn > 0
        fn_body = content[idx_fn:idx_fn + 1500]
        assert "push_notification" in fn_body


# ---------------------------------------------------------------------------
# Gap 4: Squad Org Chart Sync
# ---------------------------------------------------------------------------


class TestGap4SquadOrgChartSync:
    """Gap 4: Squad definitions sync to Paperclip org chart."""


    def test_squad_sync_hook_is_executable(self):
        hook = PROJECT_ROOT / "packages" / "paperclip-integration" / "hooks" / "paperclip-squad-sync.sh"
        assert os.access(hook, os.X_OK), "paperclip-squad-sync.sh must be executable"


# ---------------------------------------------------------------------------
# Gap 8: Client Retry Queue
# ---------------------------------------------------------------------------


class TestGap8RetryQueue:
    """Gap 8: Client queues failed requests and retries on recovery."""

    def test_client_has_retry_queue_class(self):
        sys.path.insert(0, str(PROJECT_ROOT / "lib"))
        from paperclip_client import PaperclipClient, _RetryQueue

        q = _RetryQueue()
        assert q.size() == 0

    def test_retry_queue_enqueue_and_drain(self):
        sys.path.insert(0, str(PROJECT_ROOT / "lib"))
        from paperclip_client import _RetryQueue

        q = _RetryQueue()
        q.enqueue("POST", "/api/test", {"key": "val"})
        assert q.size() == 1
        entries = q.drain()
        assert len(entries) == 1
        assert entries[0][0] == "POST"
        assert entries[0][1] == "/api/test"
        assert q.size() == 0

    def test_retry_queue_bounded_at_100(self):
        sys.path.insert(0, str(PROJECT_ROOT / "lib"))
        from paperclip_client import _RetryQueue

        q = _RetryQueue()
        for i in range(150):
            q.enqueue("POST", "/api/test/%d" % i, None)
        assert q.size() == 100  # Oldest 50 dropped

    def test_client_has_flush_retry_queue(self):
        sys.path.insert(0, str(PROJECT_ROOT / "lib"))
        from paperclip_client import PaperclipClient

        client = PaperclipClient(base_url="http://127.0.0.1:1")
        assert hasattr(client, "flush_retry_queue")
        assert hasattr(client, "retry_queue_size")
        assert client.retry_queue_size == 0

    def test_client_queues_on_connection_failure(self):
        """POST to unreachable server should queue the request."""
        sys.path.insert(0, str(PROJECT_ROOT / "lib"))
        from paperclip_client import PaperclipClient

        client = PaperclipClient(base_url="http://127.0.0.1:1")
        client.push_notification("test", "body", "info")
        assert client.retry_queue_size == 1

    def test_client_does_not_queue_health_checks(self):
        """GET health checks should NOT be queued."""
        sys.path.insert(0, str(PROJECT_ROOT / "lib"))
        from paperclip_client import PaperclipClient

        client = PaperclipClient(base_url="http://127.0.0.1:1")
        client.is_available()
        assert client.retry_queue_size == 0


# ---------------------------------------------------------------------------
# Client API completeness
# ---------------------------------------------------------------------------


class TestClientAPICompleteness:
    """Verify the client has all required methods for the 8 gaps."""

    def test_client_has_all_required_methods(self):
        sys.path.insert(0, str(PROJECT_ROOT / "lib"))
        from paperclip_client import PaperclipClient

        client = PaperclipClient(base_url="http://127.0.0.1:1")
        required_methods = [
            "is_available",
            "create_project",
            "create_issue",
            "update_issue_status",
            "update_agent_status",
            "push_spend",
            "push_notification",
            "sync_org_chart",
            "push_metrics",
            "push_kpis",
            "push_cost_events",
            "push_error_stats",
            "push_session_summary",
            "flush_retry_queue",
        ]
        for method in required_methods:
            assert hasattr(client, method), f"Client missing method: {method}"
