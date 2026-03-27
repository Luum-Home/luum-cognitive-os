"""Unit tests for lib/paperclip_client.py

Validates the PaperclipClient class: availability checks, CRUD operations,
spend/notification push, org chart sync, error handling, and URL configuration.

Author: luum
"""

import http.server
import json
import os
import threading
from typing import Any, Dict, List, Optional
from unittest import mock

import pytest

from lib.paperclip_client import (
    VALID_ISSUE_STATUSES,
    VALID_SEVERITIES,
    PaperclipClient,
    is_paperclip_available,
    get_dashboard_url,
    push_metrics,
    push_session_summary,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers -- lightweight HTTP server for integration-style unit tests
# ---------------------------------------------------------------------------


class _RecordingHandler(http.server.BaseHTTPRequestHandler):
    """Minimal HTTP handler that records requests and returns canned responses."""

    # Class-level shared state (set per-test via class attribute)
    recorded_requests: List[Dict[str, Any]] = []
    response_code: int = 200
    response_body: Dict[str, Any] = {}

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def do_PUT(self) -> None:
        self._handle()

    def _handle(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""
        parsed_body = None
        if body:
            try:
                parsed_body = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, ValueError):
                parsed_body = body.decode("utf-8")

        _RecordingHandler.recorded_requests.append(
            {
                "method": self.command,
                "path": self.path,
                "body": parsed_body,
            }
        )

        self.send_response(_RecordingHandler.response_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        resp = json.dumps(_RecordingHandler.response_body).encode("utf-8")
        self.wfile.write(resp)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress server log output during tests."""
        pass


@pytest.fixture()
def mock_server():
    """Start a local HTTP server for the duration of a test."""
    _RecordingHandler.recorded_requests = []
    _RecordingHandler.response_code = 200
    _RecordingHandler.response_body = {}

    server = http.server.HTTPServer(("127.0.0.1", 0), _RecordingHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield server, port

    server.shutdown()
    thread.join(timeout=2)


def _client_for(port: int) -> PaperclipClient:
    """Create a PaperclipClient pointing at the test server."""
    return PaperclipClient(base_url="http://127.0.0.1:%d" % port)


# ---------------------------------------------------------------------------
# Tests: availability
# ---------------------------------------------------------------------------


class TestIsAvailable:
    """Tests for PaperclipClient.is_available()."""

    def test_returns_true_when_server_responds(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {"status": "ok"}

        client = _client_for(port)
        assert client.is_available() is True

        assert len(_RecordingHandler.recorded_requests) == 1
        req = _RecordingHandler.recorded_requests[0]
        assert req["method"] == "GET"
        assert req["path"] == "/api/health"

    def test_returns_false_when_server_not_running(self):
        client = PaperclipClient(base_url="http://127.0.0.1:1")
        assert client.is_available() is False

    def test_returns_false_on_http_error(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 500
        _RecordingHandler.response_body = {"error": "internal"}

        client = _client_for(port)
        # 500 raises HTTPError via urllib, which _request catches
        assert client.is_available() is False


# ---------------------------------------------------------------------------
# Tests: create_project
# ---------------------------------------------------------------------------


class TestCreateProject:
    """Tests for PaperclipClient.create_project()."""

    def test_creates_project_with_name_and_goal(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {"id": "proj-123", "name": "auth-refactor"}

        client = _client_for(port)
        result = client.create_project("auth-refactor", "Refactor auth module")

        assert result == {"id": "proj-123", "name": "auth-refactor"}
        req = _RecordingHandler.recorded_requests[-1]
        assert req["method"] == "POST"
        assert req["path"] == "/api/projects"
        assert req["body"]["name"] == "auth-refactor"
        assert req["body"]["goal"] == "Refactor auth module"

    def test_returns_empty_dict_on_failure(self):
        client = PaperclipClient(base_url="http://127.0.0.1:1")
        result = client.create_project("test", "test goal")
        assert result == {}


# ---------------------------------------------------------------------------
# Tests: create_issue
# ---------------------------------------------------------------------------


class TestCreateIssue:
    """Tests for PaperclipClient.create_issue()."""

    def test_creates_issue_with_valid_data(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {"id": "issue-456", "title": "sdd-apply"}

        client = _client_for(port)
        result = client.create_issue(
            project_id="proj-123",
            title="sdd-apply: implement auth",
            description="Apply phase for auth refactor",
            assignee="sdd-apply-agent",
        )

        assert result["id"] == "issue-456"
        req = _RecordingHandler.recorded_requests[-1]
        assert req["body"]["project_id"] == "proj-123"
        assert req["body"]["assignee"] == "sdd-apply-agent"

    def test_creates_issue_without_assignee(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {"id": "issue-789"}

        client = _client_for(port)
        result = client.create_issue("proj-1", "title", "desc")

        req = _RecordingHandler.recorded_requests[-1]
        assert "assignee" not in req["body"]
        assert result["id"] == "issue-789"


# ---------------------------------------------------------------------------
# Tests: update_issue_status
# ---------------------------------------------------------------------------


class TestUpdateIssueStatus:
    """Tests for PaperclipClient.update_issue_status()."""

    def test_updates_status_to_in_progress(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {"id": "issue-1", "status": "in_progress"}

        client = _client_for(port)
        result = client.update_issue_status("issue-1", "in_progress")

        assert result["status"] == "in_progress"
        req = _RecordingHandler.recorded_requests[-1]
        assert req["method"] == "PUT"
        assert req["path"] == "/api/issues/issue-1/status"
        assert req["body"]["status"] == "in_progress"

    def test_rejects_invalid_status(self):
        client = PaperclipClient(base_url="http://127.0.0.1:1")
        with pytest.raises(ValueError, match="Invalid status"):
            client.update_issue_status("issue-1", "invalid_status")

    def test_all_valid_statuses_accepted(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {}

        client = _client_for(port)
        for status in VALID_ISSUE_STATUSES:
            result = client.update_issue_status("issue-1", status)
            assert result is not None


# ---------------------------------------------------------------------------
# Tests: push_spend
# ---------------------------------------------------------------------------


class TestPushSpend:
    """Tests for PaperclipClient.push_spend()."""

    def test_pushes_spend_data(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {"recorded": True}

        client = _client_for(port)
        result = client.push_spend(amount_usd=0.42, model="sonnet", tokens=15000)

        assert result == {"recorded": True}
        req = _RecordingHandler.recorded_requests[-1]
        assert req["method"] == "POST"
        assert req["path"] == "/api/spend"
        assert req["body"]["amount_usd"] == 0.42
        assert req["body"]["model"] == "sonnet"
        assert req["body"]["tokens"] == 15000


# ---------------------------------------------------------------------------
# Tests: push_notification
# ---------------------------------------------------------------------------


class TestPushNotification:
    """Tests for PaperclipClient.push_notification()."""

    def test_pushes_notification_with_defaults(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {"id": "notif-1"}

        client = _client_for(port)
        result = client.push_notification("Test Failure", "3 tests failed in api/")

        req = _RecordingHandler.recorded_requests[-1]
        assert req["path"] == "/api/notifications"
        assert req["body"]["title"] == "Test Failure"
        assert req["body"]["severity"] == "info"
        assert result["id"] == "notif-1"

    def test_pushes_critical_notification(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {}

        client = _client_for(port)
        client.push_notification("Circuit Open", "Auto-repair blocked", "critical")

        req = _RecordingHandler.recorded_requests[-1]
        assert req["body"]["severity"] == "critical"

    def test_rejects_invalid_severity(self):
        client = PaperclipClient(base_url="http://127.0.0.1:1")
        with pytest.raises(ValueError, match="Invalid severity"):
            client.push_notification("title", "body", "extreme")


# ---------------------------------------------------------------------------
# Tests: sync_org_chart
# ---------------------------------------------------------------------------


class TestSyncOrgChart:
    """Tests for PaperclipClient.sync_org_chart()."""

    def test_syncs_squad_definitions(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {"synced": 2}

        squads = [
            {
                "name": "platform-squad",
                "manager": "engineering-manager",
                "agents": [
                    {"name": "sre-agent", "role": "member"},
                    {"name": "code-reviewer", "role": "member"},
                ],
            },
            {
                "name": "product-squad",
                "agents": [{"name": "dev-agent", "role": "member"}],
            },
        ]

        client = _client_for(port)
        result = client.sync_org_chart(squads)

        assert result["synced"] == 2
        req = _RecordingHandler.recorded_requests[-1]
        assert req["path"] == "/api/org-chart"
        assert len(req["body"]["squads"]) == 2


# ---------------------------------------------------------------------------
# Tests: _request error handling
# ---------------------------------------------------------------------------


class TestRequestErrorHandling:
    """Tests for PaperclipClient._request() graceful degradation."""

    def test_handles_connection_refused(self):
        client = PaperclipClient(base_url="http://127.0.0.1:1")
        result = client._request("GET", "/api/health")
        assert result is None

    def test_handles_timeout(self):
        # Use an unreachable IP to trigger timeout behavior
        client = PaperclipClient(base_url="http://192.0.2.1:9999")
        result = client._request("GET", "/api/health")
        assert result is None

    def test_handles_http_500(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 500
        _RecordingHandler.response_body = {"error": "internal server error"}

        client = _client_for(port)
        result = client._request("GET", "/api/something")
        assert result is None

    def test_handles_empty_response_body(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {}

        client = _client_for(port)
        result = client._request("POST", "/api/test", data={"key": "val"})
        # Empty dict is returned as valid JSON {}
        assert result == {}


# ---------------------------------------------------------------------------
# Tests: URL configuration
# ---------------------------------------------------------------------------


class TestURLConfiguration:
    """Tests for URL configuration from constructor and environment."""

    def test_explicit_base_url(self):
        client = PaperclipClient(base_url="http://custom:9999")
        assert client.base_url == "http://custom:9999"

    def test_strips_trailing_slash(self):
        client = PaperclipClient(base_url="http://custom:9999/")
        assert client.base_url == "http://custom:9999"

    def test_falls_back_to_paperclip_url_env(self, monkeypatch):
        monkeypatch.setenv("PAPERCLIP_URL", "http://from-env:4000")
        monkeypatch.delenv("COGNITIVE_OS_PAPERCLIP_URL", raising=False)
        client = PaperclipClient()
        assert client.base_url == "http://from-env:4000"

    def test_falls_back_to_cognitive_os_env(self, monkeypatch):
        monkeypatch.delenv("PAPERCLIP_URL", raising=False)
        monkeypatch.setenv("COGNITIVE_OS_PAPERCLIP_URL", "http://cos-env:5000")
        client = PaperclipClient()
        assert client.base_url == "http://cos-env:5000"

    def test_paperclip_url_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("PAPERCLIP_URL", "http://primary:1111")
        monkeypatch.setenv("COGNITIVE_OS_PAPERCLIP_URL", "http://secondary:2222")
        client = PaperclipClient()
        assert client.base_url == "http://primary:1111"

    def test_defaults_to_localhost_3200(self, monkeypatch):
        monkeypatch.delenv("PAPERCLIP_URL", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PAPERCLIP_URL", raising=False)
        client = PaperclipClient()
        assert client.base_url == "http://localhost:3200"


# ---------------------------------------------------------------------------
# Tests: legacy push methods
# ---------------------------------------------------------------------------


class TestLegacyPushMethods:
    """Tests for backward-compatible push methods."""

    def test_push_metrics_returns_true_on_success(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {"ok": True}

        client = _client_for(port)
        result = client.push_metrics({"type": "test", "data": 42})
        assert result is True

    def test_push_metrics_returns_false_on_empty(self):
        client = PaperclipClient(base_url="http://127.0.0.1:1")
        assert client.push_metrics({}) is False

    def test_push_session_summary_sends_payload(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {}

        client = _client_for(port)
        summary = {
            "session_id": "s-123",
            "timestamp": "2026-03-27T12:00:00Z",
            "metrics": {"errors": 5},
        }
        result = client.push_session_summary(summary)
        assert result is True

        req = _RecordingHandler.recorded_requests[-1]
        assert req["body"]["type"] == "cognitive-os-session-summary"
        assert req["body"]["session_id"] == "s-123"

    def test_push_kpis_adds_type_field(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {}

        client = _client_for(port)
        result = client.push_kpis({"score": 85})
        assert result is True

        req = _RecordingHandler.recorded_requests[-1]
        assert req["body"]["type"] == "cognitive-os-kpis"

    def test_push_cost_events_wraps_list(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {}

        client = _client_for(port)
        events = [{"model": "sonnet", "cost": 0.05}]
        result = client.push_cost_events(events)
        assert result is True

        req = _RecordingHandler.recorded_requests[-1]
        assert req["body"]["type"] == "cognitive-os-cost-events"
        assert req["body"]["events"] == events

    def test_push_error_stats_merges_payload(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {}

        client = _client_for(port)
        stats = {"total_errors": 10, "errors_by_type": {"TEST_FAILURE": 7}}
        result = client.push_error_stats(stats)
        assert result is True

        req = _RecordingHandler.recorded_requests[-1]
        assert req["body"]["type"] == "cognitive-os-error-stats"
        assert req["body"]["total_errors"] == 10


# ---------------------------------------------------------------------------
# Tests: module-level convenience functions
# ---------------------------------------------------------------------------


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""

    def test_is_paperclip_available_returns_false_when_not_running(self, monkeypatch):
        monkeypatch.setenv("PAPERCLIP_URL", "http://127.0.0.1:1")
        # Reset the module-level default client
        import lib.paperclip_client as mod
        mod._default_client = None
        assert is_paperclip_available() is False
        mod._default_client = None  # cleanup

    def test_get_dashboard_url_returns_configured_url(self, monkeypatch):
        monkeypatch.setenv("PAPERCLIP_URL", "http://test-url:3200")
        import lib.paperclip_client as mod
        mod._default_client = None
        assert get_dashboard_url() == "http://test-url:3200"
        mod._default_client = None  # cleanup


# ---------------------------------------------------------------------------
# Tests: update_agent_status
# ---------------------------------------------------------------------------


class TestUpdateAgentStatus:
    """Tests for PaperclipClient.update_agent_status()."""

    def test_sends_status_with_heartbeat(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {"agent": "sre-agent", "status": "active"}

        client = _client_for(port)
        heartbeat = {"phase": "apply", "step": "step 3/5", "alive": True}
        result = client.update_agent_status("sre-agent", "active", heartbeat)

        assert result["status"] == "active"
        req = _RecordingHandler.recorded_requests[-1]
        assert req["body"]["agent_name"] == "sre-agent"
        assert req["body"]["heartbeat"]["phase"] == "apply"

    def test_sends_status_without_heartbeat(self, mock_server):
        _, port = mock_server
        _RecordingHandler.response_code = 200
        _RecordingHandler.response_body = {}

        client = _client_for(port)
        result = client.update_agent_status("test-agent", "idle")

        req = _RecordingHandler.recorded_requests[-1]
        assert "heartbeat" not in req["body"]
        assert req["body"]["status"] == "idle"
