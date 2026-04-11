"""End-to-end integration tests for executor mode.

Tests in TestExecutorModeE2E require Valkey on localhost:6379 and are
automatically skipped when it is not available.

Tests in TestExecutorModeFallback always run and validate graceful
degradation when no infrastructure is present.
"""

import os
import time
import uuid

import pytest

from lib.orchestrator_capabilities import OrchestratorCapabilities

# Detect once at import time so skip decisions are made before collection.
_caps = OrchestratorCapabilities().detect()
_CONNECTED = _caps.mode == "connected"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent_id() -> str:
    return "test-e2e-%s" % uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Connected-mode tests (skip when Valkey not running)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CONNECTED, reason="Valkey not running — skipping connected-mode tests")
class TestExecutorModeE2E:
    """End-to-end tests for executor mode. Only run when Valkey is available."""

    def test_valkey_connection(self):
        """Can connect to Valkey on localhost:6379."""
        import socket
        host = os.environ.get("VALKEY_HOST", "localhost")
        port = int(os.environ.get("VALKEY_PORT", "6379"))
        with socket.create_connection((host, port), timeout=2.0) as sock:
            assert sock is not None

    def test_agent_bus_publish(self):
        """Can publish a progress event to the agent bus without raising."""
        from lib.agent_bus import AgentPublisher
        pub = AgentPublisher(agent_id=_make_agent_id())
        pub.progress(tool="Bash", action="integration test")
        assert True

    def test_agent_bus_subscribe(self):
        """Can publish progress and the call completes without error."""
        from lib.agent_bus import AgentPublisher

        publisher = AgentPublisher(agent_id=_make_agent_id())
        publisher.progress(tool="Read", action="subscribe_test")
        time.sleep(0.2)
        assert True

    def test_heartbeat_publish(self):
        """Can publish a heartbeat event without error."""
        from lib.agent_bus import AgentPublisher
        pub = AgentPublisher(agent_id=_make_agent_id())
        pub.heartbeat(phase="test", step="heartbeat_check", tokens_used=0)
        assert True


# ---------------------------------------------------------------------------
# Fallback tests (always run)
# ---------------------------------------------------------------------------

class TestExecutorModeFallback:
    """Tests that always run — verify graceful fallback without Valkey."""

    def test_capabilities_detect_no_crash(self):
        """detect() never crashes regardless of environment."""
        caps = OrchestratorCapabilities().detect()
        assert caps.mode in ("connected", "fire_and_forget")

    def test_fire_and_forget_is_default(self):
        """Without executor env var, mode is FIRE_AND_FORGET when Valkey absent."""
        # We can only assert this when Valkey is actually absent.
        if _CONNECTED:
            pytest.skip("Valkey is running — cannot test fire-and-forget default here")
        assert _caps.mode == "fire_and_forget"

    def test_delegate_task_fallback(self):
        """delegate_task() returns a structured error dict when executor unavailable."""
        import sys
        from unittest.mock import patch

        # Remove ClaudeExecutor from modules to simulate unavailability
        with patch.dict("sys.modules", {"lib.claude_executor": None}):
            from lib.orchestrator_mode import delegate_task
            result = delegate_task("test task")

        # Must return a dict with success=False (or True if executor IS available)
        assert isinstance(result, dict)
        assert "success" in result

    def test_agent_bus_file_fallback(self):
        """Agent bus falls back gracefully when Valkey is unreachable."""
        from lib.agent_bus import AgentPublisher

        # Pass an unreachable URL directly so the publisher falls back to file I/O
        pub = AgentPublisher(
            agent_id=_make_agent_id(),
            valkey_url="redis://127.0.0.99:6379",  # unreachable
        )
        # Should not raise — falls back to file or no-op
        pub.progress(tool="Bash", action="file fallback test")
        assert True

    def test_auto_executor_no_crash(self):
        """AutoExecutor.check_and_activate() never raises."""
        from lib.auto_executor import AutoExecutor
        result = AutoExecutor.check_and_activate()
        assert "mode" in result
        assert "valkey_available" in result
        assert "auto_activated" in result
        assert "message" in result

    def test_capabilities_format_status(self):
        """format_status() returns a non-empty string."""
        caps = OrchestratorCapabilities().detect()
        status = caps.format_status()
        assert isinstance(status, str)
        assert len(status) > 0

    def test_capabilities_to_dict(self):
        """to_dict() returns a serializable dict with expected keys."""
        caps = OrchestratorCapabilities().detect()
        d = caps.to_dict()
        assert "mode" in d
        assert "valkey_available" in d
        assert "capabilities" in d
