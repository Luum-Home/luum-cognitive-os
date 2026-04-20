# SCOPE: both
# scope: both
"""Paperclip REST API client for Cognitive OS dashboard integration.

Paperclip is the UI layer for Cognitive OS. This client provides methods to
push SDD pipeline state, agent heartbeats, cost data, notifications, and
squad org charts to the Paperclip dashboard.

Uses only stdlib (urllib) -- no external dependencies.
Python 3.9+ compatible.

Author: luum
"""

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_BASE_URL = "http://localhost:3200"
_CONNECT_TIMEOUT = 3
_REQUEST_TIMEOUT = 10

# Issue status values accepted by Paperclip
VALID_ISSUE_STATUSES = frozenset({"open", "in_progress", "blocked", "done"})

# Notification severity levels
VALID_SEVERITIES = frozenset({"info", "warning", "critical"})


class _RetryQueue:
    """Thread-safe queue for failed Paperclip requests.

    When Paperclip is unavailable, requests are queued in memory and
    retried on the next successful call. The queue is bounded (max 100
    entries) and entries expire after 5 minutes.
    """

    _MAX_SIZE = 100
    _ENTRY_TTL_S = 300  # 5 minutes

    def __init__(self) -> None:
        self._queue: List[Tuple[float, str, str, Optional[Dict[str, Any]]]] = []
        self._lock = threading.Lock()

    def enqueue(
        self, method: str, path: str, data: Optional[Dict[str, Any]]
    ) -> None:
        """Add a failed request to the retry queue."""
        with self._lock:
            if len(self._queue) >= self._MAX_SIZE:
                # Drop oldest entry
                self._queue.pop(0)
            self._queue.append((time.time(), method, path, data))

    def drain(self) -> List[Tuple[str, str, Optional[Dict[str, Any]]]]:
        """Return all non-expired entries and clear the queue."""
        now = time.time()
        with self._lock:
            live = [
                (m, p, d)
                for (ts, m, p, d) in self._queue
                if (now - ts) < self._ENTRY_TTL_S
            ]
            self._queue.clear()
            return live

    def size(self) -> int:
        """Return current queue size."""
        with self._lock:
            return len(self._queue)


class PaperclipClient:
    """REST API client for Paperclip dashboard integration.

    Args:
        base_url: Paperclip server URL. Falls back to PAPERCLIP_URL or
            COGNITIVE_OS_PAPERCLIP_URL environment variables, then to
            http://localhost:3200.
        enable_retry_queue: If True (default), failed requests are queued
            in memory and retried on the next successful request.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        enable_retry_queue: bool = True,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("PAPERCLIP_URL")
            or os.environ.get("COGNITIVE_OS_PAPERCLIP_URL")
            or _DEFAULT_BASE_URL
        ).rstrip("/")
        self._retry_queue: Optional[_RetryQueue] = (
            _RetryQueue() if enable_retry_queue else None
        )

    # -------------------------------------------------------------------
    # Health / availability
    # -------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check if Paperclip is running and reachable.

        Performs a GET to /api/health with a short timeout.

        Returns:
            True if the server responds with a 2xx status.
        """
        result = self._request("GET", "/api/health")
        return result is not None

    # -------------------------------------------------------------------
    # Projects (SDD changes)
    # -------------------------------------------------------------------

    def create_project(self, name: str, goal: str) -> Dict[str, Any]:
        """Create a project in Paperclip (maps to an SDD change).

        Args:
            name: Project name (typically the SDD change name).
            goal: One-line description of the change goal.

        Returns:
            Dict with project data including ``id``, or empty dict on failure.
        """
        payload = {"name": name, "goal": goal}
        return self._request("POST", "/api/projects", data=payload) or {}

    # -------------------------------------------------------------------
    # Issues (SDD phase tasks)
    # -------------------------------------------------------------------

    def create_issue(
        self,
        project_id: str,
        title: str,
        description: str,
        assignee: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an issue within a project (maps to an SDD phase task).

        Args:
            project_id: Parent project identifier.
            title: Issue title (e.g. "sdd-apply: implement auth flow").
            description: Detailed description of the phase task.
            assignee: Optional agent or user name assigned to the issue.

        Returns:
            Dict with issue data including ``id``, or empty dict on failure.
        """
        payload: Dict[str, Any] = {
            "project_id": project_id,
            "title": title,
            "description": description,
        }
        if assignee:
            payload["assignee"] = assignee
        return self._request("POST", "/api/issues", data=payload) or {}

    def update_issue_status(self, issue_id: str, status: str) -> Dict[str, Any]:
        """Update the status of an existing issue.

        Args:
            issue_id: Issue identifier to update.
            status: New status. Must be one of: open, in_progress, blocked, done.

        Returns:
            Dict with updated issue data, or empty dict on failure.

        Raises:
            ValueError: If ``status`` is not a valid status string.
        """
        if status not in VALID_ISSUE_STATUSES:
            raise ValueError(
                "Invalid status '%s'. Must be one of: %s"
                % (status, ", ".join(sorted(VALID_ISSUE_STATUSES)))
            )
        payload = {"status": status}
        return (
            self._request("PUT", "/api/issues/%s/status" % issue_id, data=payload)
            or {}
        )

    # -------------------------------------------------------------------
    # Agent status
    # -------------------------------------------------------------------

    def update_agent_status(
        self,
        agent_name: str,
        status: str,
        heartbeat: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update agent status with optional heartbeat data.

        Args:
            agent_name: Agent identifier (e.g. "sdd-apply-agent").
            status: Agent status string (e.g. "active", "idle", "dead").
            heartbeat: Optional heartbeat payload from Agent Bus containing
                phase, step, tokens_used, alive, etc.

        Returns:
            Dict with agent status confirmation, or empty dict on failure.
        """
        payload: Dict[str, Any] = {
            "agent_name": agent_name,
            "status": status,
        }
        if heartbeat:
            payload["heartbeat"] = heartbeat
        return self._request("POST", "/api/agents/status", data=payload) or {}

    # -------------------------------------------------------------------
    # Spend tracking
    # -------------------------------------------------------------------

    def push_spend(
        self,
        amount_usd: float,
        model: str,
        tokens: int,
    ) -> Dict[str, Any]:
        """Push a cost/spend data point to Paperclip tracking.

        Args:
            amount_usd: Dollar amount spent.
            model: Model identifier (e.g. "sonnet", "opus").
            tokens: Total tokens consumed (input + output).

        Returns:
            Dict with spend acknowledgment, or empty dict on failure.
        """
        payload = {
            "amount_usd": amount_usd,
            "model": model,
            "tokens": tokens,
        }
        return self._request("POST", "/api/spend", data=payload) or {}

    # -------------------------------------------------------------------
    # Notifications (inbox)
    # -------------------------------------------------------------------

    def push_notification(
        self,
        title: str,
        body: str,
        severity: str = "info",
    ) -> Dict[str, Any]:
        """Push a notification to the Paperclip inbox.

        Args:
            title: Notification title.
            body: Notification body text.
            severity: One of: info, warning, critical. Defaults to "info".

        Returns:
            Dict with notification acknowledgment, or empty dict on failure.

        Raises:
            ValueError: If ``severity`` is not a valid value.
        """
        if severity not in VALID_SEVERITIES:
            raise ValueError(
                "Invalid severity '%s'. Must be one of: %s"
                % (severity, ", ".join(sorted(VALID_SEVERITIES)))
            )
        payload = {
            "title": title,
            "body": body,
            "severity": severity,
        }
        return self._request("POST", "/api/notifications", data=payload) or {}

    # -------------------------------------------------------------------
    # Org chart (squads)
    # -------------------------------------------------------------------

    def sync_org_chart(self, squads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sync squad definitions to the Paperclip org chart.

        Args:
            squads: List of squad dicts. Each dict should contain:
                - name: Squad name
                - agents: List of agent dicts with name and role
                - manager: Manager agent name (optional)

        Returns:
            Dict with sync confirmation, or empty dict on failure.
        """
        payload = {"squads": squads}
        return self._request("POST", "/api/org-chart", data=payload) or {}

    # -------------------------------------------------------------------
    # Legacy push methods (kept for backward compatibility with sync hook)
    # -------------------------------------------------------------------

    def push_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Push raw metrics data to Paperclip.

        Args:
            metrics: Dict containing metrics data with a ``type`` field.

        Returns:
            True if successfully pushed, False otherwise.
        """
        if not metrics:
            logger.warning("Empty metrics payload, skipping push")
            return False
        return self._request("POST", "/api/artifacts", data=metrics) is not None

    def push_kpis(self, kpi_data: Dict[str, Any]) -> bool:
        """Push KPI dashboard data to Paperclip.

        Args:
            kpi_data: Dict containing KPI snapshot.

        Returns:
            True if successfully pushed, False otherwise.
        """
        if not kpi_data:
            logger.warning("Empty KPI payload, skipping push")
            return False
        if "type" not in kpi_data:
            kpi_data = {**kpi_data, "type": "cognitive-os-kpis"}
        return self._request("POST", "/api/artifacts", data=kpi_data) is not None

    def push_cost_events(self, events: List[Dict[str, Any]]) -> bool:
        """Push cost tracking events to Paperclip.

        Args:
            events: List of cost event dicts.

        Returns:
            True if successfully pushed, False otherwise.
        """
        if not events:
            logger.warning("Empty cost events list, skipping push")
            return False
        payload = {"type": "cognitive-os-cost-events", "events": events}
        return self._request("POST", "/api/artifacts", data=payload) is not None

    def push_error_stats(self, stats: Dict[str, Any]) -> bool:
        """Push error learning statistics to Paperclip.

        Args:
            stats: Dict with error learning summary.

        Returns:
            True if successfully pushed, False otherwise.
        """
        if not stats:
            logger.warning("Empty error stats payload, skipping push")
            return False
        payload = {"type": "cognitive-os-error-stats", **stats}
        return self._request("POST", "/api/artifacts", data=payload) is not None

    def push_session_summary(self, summary: Dict[str, Any]) -> bool:
        """Push a complete session summary to Paperclip.

        Args:
            summary: Dict with full session summary including metrics,
                KPIs, cost events, and error stats.

        Returns:
            True if successfully pushed, False otherwise.
        """
        if not summary:
            logger.warning("Empty session summary, skipping push")
            return False
        payload = {"type": "cognitive-os-session-summary", **summary}
        return self._request("POST", "/api/artifacts", data=payload) is not None

    # -------------------------------------------------------------------
    # Internal HTTP transport
    # -------------------------------------------------------------------

    def flush_retry_queue(self) -> int:
        """Retry all queued requests. Returns the number successfully sent."""
        if not self._retry_queue:
            return 0
        entries = self._retry_queue.drain()
        sent = 0
        for method, path, data in entries:
            result = self._request(method, path, data, _skip_queue=True)
            if result is not None:
                sent += 1
            # If it fails again, it goes back in the queue via _request
        return sent

    @property
    def retry_queue_size(self) -> int:
        """Number of requests currently queued for retry."""
        return self._retry_queue.size() if self._retry_queue else 0

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        _skip_queue: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Make an HTTP request to the Paperclip API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: API path (e.g. "/api/health").
            data: Optional dict to JSON-encode as the request body.
            _skip_queue: Internal flag to prevent infinite queue loops.

        Returns:
            Parsed JSON response as a dict, or None on any failure
            (connection refused, timeout, non-2xx status, parse error).
        """
        url = "%s%s" % (self.base_url, path)
        headers = {"Content-Type": "application/json"}

        body: Optional[bytes] = None
        if data is not None:
            body = json.dumps(data, default=str).encode("utf-8")

        timeout = _CONNECT_TIMEOUT if method == "GET" else _REQUEST_TIMEOUT

        req = urllib.request.Request(
            url, data=body, headers=headers, method=method
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_body = resp.read().decode("utf-8")
                # On success, try flushing queued requests
                if self._retry_queue and self._retry_queue.size() > 0 and not _skip_queue:
                    self.flush_retry_queue()
                if resp_body:
                    return json.loads(resp_body)
                # Empty body but 2xx status -- return an empty success dict
                return {}
        except urllib.error.HTTPError as exc:
            logger.debug(
                "Paperclip %s %s returned HTTP %d", method, path, exc.code
            )
            return None
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            logger.debug("Paperclip %s %s failed: %s", method, path, exc)
            # Queue for retry if it's a write (not health check GETs)
            if (
                self._retry_queue
                and not _skip_queue
                and method in ("POST", "PUT")
                and path != "/api/health"
            ):
                self._retry_queue.enqueue(method, path, data)
            return None
        except (json.JSONDecodeError, ValueError) as exc:
            logger.debug(
                "Paperclip %s %s response parse error: %s", method, path, exc
            )
            return None


# ---------------------------------------------------------------------------
# Module-level convenience functions (backward compatibility)
# ---------------------------------------------------------------------------

_default_client: Optional[PaperclipClient] = None


def _get_default_client() -> PaperclipClient:
    """Return (or create) the module-level default client."""
    global _default_client
    if _default_client is None:
        _default_client = PaperclipClient()
    return _default_client


def is_paperclip_available() -> bool:
    """Check if Paperclip server is reachable (module-level convenience)."""
    return _get_default_client().is_available()


def get_dashboard_url() -> str:
    """Return the Paperclip dashboard URL (module-level convenience)."""
    return _get_default_client().base_url


def push_metrics(metrics: Dict[str, Any]) -> bool:
    """Push raw metrics (module-level convenience)."""
    return _get_default_client().push_metrics(metrics)


def push_kpis(kpi_data: Dict[str, Any]) -> bool:
    """Push KPI data (module-level convenience)."""
    return _get_default_client().push_kpis(kpi_data)


def push_cost_events(events: List[Dict[str, Any]]) -> bool:
    """Push cost events (module-level convenience)."""
    return _get_default_client().push_cost_events(events)


def push_error_stats(stats: Dict[str, Any]) -> bool:
    """Push error stats (module-level convenience)."""
    return _get_default_client().push_error_stats(stats)


def push_session_summary(summary: Dict[str, Any]) -> bool:
    """Push session summary (module-level convenience)."""
    return _get_default_client().push_session_summary(summary)
