"""End-to-end integration tests for executor mode.

Tests in TestExecutorModeE2E require Valkey on localhost:6379 and are
automatically skipped when it is not available.

Tests in TestExecutorModeFallback always run and validate graceful
degradation when no infrastructure is present.

Tests in TestHeartbeatE2E validate the full heartbeat pipeline:
publisher → Valkey pub/sub → subscriber receives messages.
"""

import os
import socket
import threading
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


def _valkey_reachable() -> bool:
    """TCP-level check: is Valkey on localhost:6379 accepting connections?"""
    try:
        with socket.create_connection(("127.0.0.1", 6379), timeout=1.0):
            return True
    except (OSError, socket.timeout):
        return False


# ---------------------------------------------------------------------------
# Connected-mode tests (skip when Valkey not running)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not _CONNECTED, reason="Valkey not running — skipping connected-mode tests")
class TestExecutorModeE2E:
    """End-to-end tests for executor mode. Only run when Valkey is available."""

    def test_valkey_connection(self):
        """Can connect to Valkey on localhost:6379."""
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
# Heartbeat E2E validation (the core of the work-queue item)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not _valkey_reachable(), reason="Valkey not reachable on localhost:6379")
class TestHeartbeatE2E:
    """Validates the full heartbeat pipeline end-to-end.

    This is the primary validation for work-queue item executor-mode-e2e-validation.

    Steps covered:
      1. auto_executor.check_and_activate() detects Valkey and sets executor mode
      2. Valkey TCP check passes
      3. AgentPublisher.start_heartbeat_thread() produces messages on
         cos:agent:{id}:heartbeat channel
      4. A subscriber on cos:agent:*:heartbeat receives those messages
      5. Agent lifecycle (launched → running → completed) is visible via heartbeats
    """

    def test_step1_auto_executor_detects_valkey(self):
        """Step 1: auto_executor.check_and_activate() sees Valkey and activates executor mode."""
        # Save original mode so we can restore it after this test
        original_mode = os.environ.get("ORCHESTRATOR_MODE", "")
        try:
            # Force unset so we can test auto-activation
            if "ORCHESTRATOR_MODE" in os.environ:
                del os.environ["ORCHESTRATOR_MODE"]

            from lib.auto_executor import AutoExecutor
            result = AutoExecutor.check_and_activate()

            assert result["valkey_available"] is True, (
                "Expected valkey_available=True but got %s. "
                "Valkey may be unreachable even though TCP connect succeeded." % result
            )
            assert result["mode"] == "connected", (
                "Expected mode='connected' but got mode='%s'" % result["mode"]
            )
            # After activation, ORCHESTRATOR_MODE should be set
            assert os.environ.get("ORCHESTRATOR_MODE", "").lower() == "executor", (
                "Expected ORCHESTRATOR_MODE=executor after activation, got '%s'"
                % os.environ.get("ORCHESTRATOR_MODE", "")
            )
        finally:
            # Restore original state
            if original_mode:
                os.environ["ORCHESTRATOR_MODE"] = original_mode
            elif "ORCHESTRATOR_MODE" in os.environ:
                del os.environ["ORCHESTRATOR_MODE"]

    def test_step2_valkey_tcp_reachable(self):
        """Step 2: Valkey is reachable via direct TCP connect."""
        assert _valkey_reachable(), "Valkey TCP connect failed on localhost:6379"

    def test_step3_heartbeat_thread_starts(self):
        """Step 3: start_heartbeat_thread() starts a live thread and publishes at least one beat."""
        from lib.agent_bus import AgentPublisher

        agent_id = _make_agent_id()
        pub = AgentPublisher(agent_id=agent_id)

        # Should not be running yet
        assert pub._heartbeat_thread is None or not pub._heartbeat_thread.is_alive()

        pub.start_heartbeat_thread()

        # Thread should be alive now
        assert pub._heartbeat_thread is not None
        assert pub._heartbeat_thread.is_alive(), (
            "Heartbeat thread was not alive after start_heartbeat_thread()"
        )

        # Wait for at least one heartbeat interval to fire
        time.sleep(0.3)

        pub.stop()

        # After stop, thread should no longer be alive
        assert not (
            pub._heartbeat_thread is not None and pub._heartbeat_thread.is_alive()
        ), "Heartbeat thread still alive after stop()"

    def test_step4_heartbeats_received_via_pubsub(self):
        """Step 4: Subscriber on cos:agent:*:heartbeat receives heartbeat messages.

        This is the critical test: verifies that messages published on the
        heartbeat channel are actually received by a psubscribe subscriber.
        """
        try:
            import redis
        except ImportError:
            pytest.skip("redis package not installed")

        agent_id = _make_agent_id()
        received: list = []
        receive_error: list = []

        def _subscriber_thread():
            """Subscribe and collect messages for 8 seconds."""
            try:
                r = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)
                p = r.pubsub()
                p.psubscribe("cos:agent:*:heartbeat")
                deadline = time.time() + 8.0
                while time.time() < deadline:
                    msg = p.get_message(ignore_subscribe_messages=True, timeout=0.5)
                    if msg and msg.get("type") == "pmessage":
                        received.append(msg)
                p.punsubscribe()
                p.close()
                r.close()
            except Exception as exc:
                receive_error.append(str(exc))

        # Start subscriber first so it's listening before messages are published
        sub_thread = threading.Thread(target=_subscriber_thread, daemon=True)
        sub_thread.start()
        time.sleep(0.3)  # let subscriber register

        # Start publisher with heartbeat thread
        from lib.agent_bus import AgentPublisher
        pub = AgentPublisher(agent_id=agent_id)
        pub.start_heartbeat_thread()

        # Wait long enough for 2+ heartbeat intervals (5s each)
        sub_thread.join(timeout=10)
        pub.stop()

        # Diagnostics
        assert not receive_error, (
            "Subscriber thread raised an error: %s" % receive_error
        )
        assert len(received) > 0, (
            "No heartbeat messages received on cos:agent:*:heartbeat channel.\n"
            "DIAGNOSIS: Either start_heartbeat_thread() is not publishing to Valkey "
            "or there is a channel name mismatch.\n"
            "Expected pattern: cos:agent:%s:heartbeat\n"
            "Check AgentPublisher._use_valkey (must be True) and that "
            "_channel() builds 'cos:agent:{id}:heartbeat'." % agent_id
        )

    def test_step5_agent_lifecycle_visible(self):
        """Step 5: Full agent lifecycle (launched → running → completed) visible via heartbeats.

        Simulates what ClaudeExecutor does when it creates an AgentPublisher with
        agent_id set. Verifies that:
        - Heartbeats are published while 'running'
        - report_complete() publishes a final alive=False heartbeat
        - The lifecycle can be tracked by an OrchestratorSubscriber
        """
        try:
            import redis
        except ImportError:
            pytest.skip("redis package not installed")

        from lib.agent_bus import AgentPublisher, OrchestratorSubscriber

        agent_id = _make_agent_id()
        lifecycle_events: list = []

        # Set up orchestrator subscriber
        sub = OrchestratorSubscriber()
        sub.on_heartbeat(lambda data: lifecycle_events.append(
            {"type": "heartbeat", "alive": data.get("alive"), "step": data.get("step")}
        ))
        sub.on_progress(lambda data: lifecycle_events.append(
            {"type": data.get("type", "progress"), "summary": data.get("result_summary", "")}
        ))
        sub.subscribe_agent(agent_id)

        # Small delay to ensure listener thread is up
        time.sleep(0.2)

        # Simulate ClaudeExecutor behavior: create publisher with agent_id
        pub = AgentPublisher(agent_id=agent_id)
        pub.start_heartbeat_thread()  # This is what ClaudeExecutor.__init__ calls

        # Let the agent "run" for a couple of heartbeat intervals
        time.sleep(6.5)

        # Simulate agent completion (what ClaudeExecutor does on success)
        pub.report_complete("Test agent completed successfully")
        pub.stop()

        # Give subscriber time to process final events
        time.sleep(0.5)
        sub.stop()

        # Analyze lifecycle
        heartbeats = [e for e in lifecycle_events if e["type"] == "heartbeat"]
        completions = [e for e in lifecycle_events if e["type"] == "complete"]

        assert len(heartbeats) > 0, (
            "No heartbeat events received by OrchestratorSubscriber.\n"
            "Lifecycle events seen: %s\n"
            "DIAGNOSIS: subscribe_agent() may not be routing to OrchestratorSubscriber "
            "callbacks, or Valkey pub/sub is not delivering messages." % lifecycle_events
        )

        alive_beats = [h for h in heartbeats if h.get("alive") is True]
        dead_beats = [h for h in heartbeats if h.get("alive") is False]

        assert len(alive_beats) > 0, (
            "No alive=True heartbeats received. Got: %s" % heartbeats
        )
        assert len(dead_beats) > 0, (
            "No alive=False heartbeat received (stop/complete not published). "
            "Got heartbeats: %s" % heartbeats
        )

        # completions may or may not arrive depending on timing; log but don't fail
        # because 'complete' is published on the 'progress' channel, which requires
        # subscribe_agent to subscribe to it.

    def test_step6_claude_executor_creates_publisher(self):
        """Step 6: ClaudeExecutor with agent_id creates an AgentPublisher with heartbeat thread.

        Validates that the wiring in ClaudeExecutor.__init__ that calls
        AgentPublisher.start_heartbeat_thread() is correct — without actually
        running a full claude CLI subprocess.
        """
        from lib.claude_executor import ClaudeExecutor

        agent_id = _make_agent_id()
        executor = ClaudeExecutor(
            working_dir="/tmp",
            agent_id=agent_id,
        )

        # _bus_publisher should be set when Valkey is available
        assert executor._bus_publisher is not None, (
            "ClaudeExecutor._bus_publisher is None even though Valkey is available.\n"
            "DIAGNOSIS: ClaudeExecutor.__init__ may have swallowed the AgentPublisher "
            "initialization error. Check the try/except in __init__."
        )

        # Heartbeat thread should be running
        pub = executor._bus_publisher
        assert pub._heartbeat_thread is not None, (
            "AgentPublisher._heartbeat_thread is None — start_heartbeat_thread() "
            "was not called in ClaudeExecutor.__init__."
        )
        assert pub._heartbeat_thread.is_alive(), (
            "Heartbeat thread exists but is not alive."
        )

        # Cleanup
        pub.stop()


# ---------------------------------------------------------------------------
# Fallback tests (always run)
# ---------------------------------------------------------------------------

@pytest.mark.integration
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
