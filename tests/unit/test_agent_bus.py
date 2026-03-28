"""Comprehensive tests for lib/agent_bus.py -- Agent Communication Bus.

Tests cover AgentPublisher, OrchestratorSubscriber, file fallback,
integration flows, and edge cases. All tests mock the redis client
so no actual Valkey/Redis server is needed.

Run with: pytest tests/unit/test_agent_bus.py -v
"""

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Ensure project root is importable
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lib.agent_bus import (
    AgentPublisher,
    OrchestratorSubscriber,
    _FileFallback,
    _sanitize_agent_id,
    _channel,
    _pattern_channel,
    is_valkey_available,
    HEARTBEAT_INTERVAL_S,
    HEARTBEAT_TIMEOUT_S,
    MAX_MESSAGE_BYTES,
    VALID_CONTROL_COMMANDS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_fallback_dir(tmp_path):
    """Provide a temporary fallback directory."""
    return str(tmp_path / "agent-bus")


@pytest.fixture
def mock_redis_module():
    """Provide a mock redis module and client."""
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.publish.return_value = 1
    mock_client.close.return_value = None

    mock_pubsub = MagicMock()
    mock_pubsub.subscribe.return_value = None
    mock_pubsub.psubscribe.return_value = None
    mock_pubsub.unsubscribe.return_value = None
    mock_pubsub.punsubscribe.return_value = None
    mock_pubsub.close.return_value = None
    mock_pubsub.get_message.return_value = None

    mock_client.pubsub.return_value = mock_pubsub

    mock_redis = MagicMock()
    mock_redis.Redis.from_url.return_value = mock_client

    return mock_redis, mock_client, mock_pubsub


@pytest.fixture
def publisher_with_valkey(mock_redis_module, tmp_fallback_dir):
    """Create an AgentPublisher connected to mock Valkey."""
    mock_redis, mock_client, _ = mock_redis_module
    with patch.dict("sys.modules", {"redis": mock_redis}):
        pub = AgentPublisher(
            agent_id="test-agent-1",
            valkey_url="redis://localhost:6379",
            fallback_dir=tmp_fallback_dir,
        )
    pub._use_valkey = True
    pub._client = mock_client
    yield pub, mock_client
    # Ensure heartbeat thread is stopped on teardown
    pub._heartbeat_stop.set()
    if pub._heartbeat_thread is not None:
        pub._heartbeat_thread.join(timeout=2)
        pub._heartbeat_thread = None


@pytest.fixture
def publisher_no_valkey(tmp_fallback_dir):
    """Create an AgentPublisher with no Valkey (file fallback)."""
    with patch.dict("sys.modules", {"redis": MagicMock(side_effect=ImportError)}):
        pub = AgentPublisher.__new__(AgentPublisher)
        pub.agent_id = "test-agent-2"
        pub.valkey_url = "redis://localhost:6379"
        pub._fallback = _FileFallback(tmp_fallback_dir)
        pub._client = None
        pub._pubsub = None
        pub._heartbeat_thread = None
        pub._heartbeat_stop = threading.Event()
        pub._lock = threading.Lock()
        pub._phase = "unknown"
        pub._step = ""
        pub._tokens_used = 0
        pub._use_valkey = False
    return pub


@pytest.fixture
def subscriber_with_valkey(mock_redis_module, tmp_fallback_dir):
    """Create an OrchestratorSubscriber connected to mock Valkey."""
    mock_redis, mock_client, mock_pubsub = mock_redis_module
    with patch.dict("sys.modules", {"redis": mock_redis}):
        sub = OrchestratorSubscriber(
            valkey_url="redis://localhost:6379",
            fallback_dir=tmp_fallback_dir,
        )
    sub._use_valkey = True
    sub._client = mock_client
    sub._pubsub = mock_pubsub
    yield sub, mock_client, mock_pubsub
    # Ensure listener thread is stopped on teardown
    sub._listener_stop.set()
    if sub._listener_thread is not None:
        sub._listener_thread.join(timeout=2)
        sub._listener_thread = None


# ---------------------------------------------------------------------------
# Helper Functions Tests
# ---------------------------------------------------------------------------

class TestSanitizeAgentId:
    def test_alphanumeric_passes_through(self):
        assert _sanitize_agent_id("agent-1") == "agent-1"

    def test_dots_and_underscores_preserved(self):
        assert _sanitize_agent_id("agent.v2_beta") == "agent.v2_beta"

    def test_special_chars_replaced(self):
        assert _sanitize_agent_id("agent:1/bad!") == "agent_1_bad_"

    def test_empty_string_returns_unknown(self):
        assert _sanitize_agent_id("") == "unknown"

    def test_spaces_replaced(self):
        assert _sanitize_agent_id("my agent") == "my_agent"

    def test_unicode_replaced(self):
        result = _sanitize_agent_id("agent-\u00e9\u00e8")
        assert ":" not in result
        assert "/" not in result


class TestChannelNames:
    def test_channel_format(self):
        assert _channel("agent-1", "heartbeat") == "cos:agent:agent-1:heartbeat"

    def test_channel_sanitizes_id(self):
        assert _channel("bad:id", "progress") == "cos:agent:bad_id:progress"

    def test_pattern_channel(self):
        assert _pattern_channel("heartbeat") == "cos:agent:*:heartbeat"


class TestIsValkeyAvailable:
    def test_available_returns_true(self, mock_redis_module):
        mock_redis, _, _ = mock_redis_module
        with patch.dict("sys.modules", {"redis": mock_redis}):
            assert is_valkey_available() is True

    def test_unavailable_returns_false(self):
        mock_redis = MagicMock()
        mock_redis.Redis.from_url.side_effect = ConnectionError("refused")
        with patch.dict("sys.modules", {"redis": mock_redis}):
            assert is_valkey_available() is False

    def test_import_error_returns_false(self):
        # If redis module not installed
        with patch("builtins.__import__", side_effect=ImportError):
            assert is_valkey_available() is False


# ---------------------------------------------------------------------------
# FileFallback Tests
# ---------------------------------------------------------------------------

class TestFileFallback:
    def test_publish_creates_directory(self, tmp_fallback_dir):
        fb = _FileFallback(tmp_fallback_dir)
        fb.publish("cos:agent:test:heartbeat", {"type": "heartbeat", "alive": True})
        assert (Path(tmp_fallback_dir) / "test" / "heartbeat.jsonl").exists()

    def test_publish_appends_jsonl(self, tmp_fallback_dir):
        fb = _FileFallback(tmp_fallback_dir)
        fb.publish("cos:agent:test:heartbeat", {"n": 1})
        fb.publish("cos:agent:test:heartbeat", {"n": 2})
        filepath = Path(tmp_fallback_dir) / "test" / "heartbeat.jsonl"
        lines = filepath.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_read_events_returns_all(self, tmp_fallback_dir):
        fb = _FileFallback(tmp_fallback_dir)
        fb.publish("cos:agent:myagent:progress", {"type": "progress", "timestamp_epoch": 100})
        fb.publish("cos:agent:myagent:progress", {"type": "progress", "timestamp_epoch": 200})
        events = fb.read_events("myagent", "progress")
        assert len(events) == 2

    def test_read_events_filters_by_time(self, tmp_fallback_dir):
        fb = _FileFallback(tmp_fallback_dir)
        fb.publish("cos:agent:ag:heartbeat", {"timestamp_epoch": 100})
        fb.publish("cos:agent:ag:heartbeat", {"timestamp_epoch": 200})
        events = fb.read_events("ag", "heartbeat", since_epoch=150)
        assert len(events) == 1
        assert events[0]["timestamp_epoch"] == 200

    def test_read_events_missing_file_returns_empty(self, tmp_fallback_dir):
        fb = _FileFallback(tmp_fallback_dir)
        events = fb.read_events("nonexistent", "heartbeat")
        assert events == []

    def test_read_events_handles_bad_json(self, tmp_fallback_dir):
        fb = _FileFallback(tmp_fallback_dir)
        agent_dir = Path(tmp_fallback_dir) / "bad"
        agent_dir.mkdir(parents=True)
        filepath = agent_dir / "heartbeat.jsonl"
        filepath.write_text('{"valid": true, "timestamp_epoch": 1}\nnot json\n{"also": "valid", "timestamp_epoch": 2}\n')
        events = fb.read_events("bad", "heartbeat")
        assert len(events) == 2


# ---------------------------------------------------------------------------
# AgentPublisher Tests
# ---------------------------------------------------------------------------

class TestAgentPublisherHeartbeat:
    def test_heartbeat_publishes_correct_channel(self, publisher_with_valkey):
        pub, mock_client = publisher_with_valkey
        pub.heartbeat(phase="apply", step="step-1", tokens_used=500)
        mock_client.publish.assert_called_once()
        channel = mock_client.publish.call_args[0][0]
        assert channel == "cos:agent:test-agent-1:heartbeat"

    def test_heartbeat_publishes_correct_format(self, publisher_with_valkey):
        pub, mock_client = publisher_with_valkey
        pub.heartbeat(phase="verify", step="step-2", tokens_used=1000)
        payload = json.loads(mock_client.publish.call_args[0][1])
        assert payload["type"] == "heartbeat"
        assert payload["phase"] == "verify"
        assert payload["step"] == "step-2"
        assert payload["tokens_used"] == 1000
        assert payload["alive"] is True
        assert "timestamp" in payload
        assert "agent_id" in payload

    def test_heartbeat_remembers_state(self, publisher_with_valkey):
        pub, mock_client = publisher_with_valkey
        pub.heartbeat(phase="apply", step="step-1", tokens_used=100)
        pub.heartbeat()  # Should use remembered values
        payload = json.loads(mock_client.publish.call_args[0][1])
        assert payload["phase"] == "apply"
        assert payload["step"] == "step-1"
        assert payload["tokens_used"] == 100


class TestAgentPublisherProgress:
    def test_progress_publishes_all_fields(self, publisher_with_valkey):
        pub, mock_client = publisher_with_valkey
        pub.progress(
            tool="Edit",
            file="src/main.go",
            action="modify function",
            step_current=3,
            step_total=10,
        )
        payload = json.loads(mock_client.publish.call_args[0][1])
        assert payload["type"] == "progress"
        assert payload["tool"] == "Edit"
        assert payload["file"] == "src/main.go"
        assert payload["action"] == "modify function"
        assert payload["step_current"] == 3
        assert payload["step_total"] == 10

    def test_progress_channel_is_correct(self, publisher_with_valkey):
        pub, mock_client = publisher_with_valkey
        pub.progress(tool="Read", file="test.go")
        channel = mock_client.publish.call_args[0][0]
        assert channel == "cos:agent:test-agent-1:progress"


@pytest.mark.timeout(10)
class TestAgentPublisherClarification:
    def test_ask_clarification_publishes_question(self, publisher_with_valkey):
        pub, mock_client = publisher_with_valkey

        # Make ask_clarification return quickly (timeout=0 for non-blocking)
        # The subscribe client will also be mocked
        mock_sub_client = MagicMock()
        mock_sub_pubsub = MagicMock()
        mock_sub_pubsub.get_message.return_value = None
        mock_sub_client.pubsub.return_value = mock_sub_pubsub

        import importlib
        mock_redis = MagicMock()
        mock_redis.Redis.from_url.side_effect = [mock_client, mock_sub_client]

        with patch.dict("sys.modules", {"redis": mock_redis}):
            result = pub.ask_clarification(
                questions=["What port?", "Which service?"],
                round_num=1,
                timeout=1,
            )
        # Should have published the question
        assert mock_client.publish.call_count >= 1
        first_call = mock_client.publish.call_args_list[0]
        assert "question" in first_call[0][0]

    def test_ask_clarification_timeout_returns_empty(self, publisher_with_valkey):
        pub, mock_client = publisher_with_valkey

        mock_sub_client = MagicMock()
        mock_sub_pubsub = MagicMock()
        mock_sub_pubsub.get_message.return_value = None
        mock_sub_client.pubsub.return_value = mock_sub_pubsub

        mock_redis = MagicMock()
        mock_redis.Redis.from_url.side_effect = [mock_client, mock_sub_client]

        with patch.dict("sys.modules", {"redis": mock_redis}):
            result = pub.ask_clarification(["question?"], timeout=1)
        assert result == []

    def test_ask_clarification_empty_questions_returns_empty(self, publisher_with_valkey):
        pub, _ = publisher_with_valkey
        result = pub.ask_clarification([], timeout=0)
        assert result == []


class TestAgentPublisherCompletion:
    def test_report_complete_publishes_summary(self, publisher_with_valkey):
        pub, mock_client = publisher_with_valkey
        pub.report_complete("All tests pass, 42 files modified")
        # Should publish both completion progress and final heartbeat
        assert mock_client.publish.call_count == 2
        # First call: completion
        payload1 = json.loads(mock_client.publish.call_args_list[0][0][1])
        assert payload1["type"] == "complete"
        assert "42 files" in payload1["result_summary"]
        # Second call: dead heartbeat
        payload2 = json.loads(mock_client.publish.call_args_list[1][0][1])
        assert payload2["alive"] is False

    def test_report_error_publishes_error(self, publisher_with_valkey):
        pub, mock_client = publisher_with_valkey
        pub.report_error("Build failed: missing import")
        payload = json.loads(mock_client.publish.call_args[0][1])
        assert payload["type"] == "error"
        assert "missing import" in payload["error"]


@pytest.mark.timeout(10)
class TestAgentPublisherHeartbeatThread:
    def test_start_heartbeat_thread(self, publisher_with_valkey):
        pub, mock_client = publisher_with_valkey
        pub.start_heartbeat_thread()
        assert pub._heartbeat_thread is not None
        assert pub._heartbeat_thread.is_alive()
        time.sleep(0.2)  # Let at least one heartbeat fire
        pub.stop()
        assert not pub._heartbeat_thread or not pub._heartbeat_thread.is_alive()
        assert mock_client.publish.call_count >= 1

    def test_stop_sends_alive_false(self, publisher_with_valkey):
        pub, mock_client = publisher_with_valkey
        pub.stop()
        last_payload = json.loads(mock_client.publish.call_args[0][1])
        assert last_payload["alive"] is False
        assert last_payload["step"] == "stopped"

    def test_double_start_is_safe(self, publisher_with_valkey):
        pub, _ = publisher_with_valkey
        pub.start_heartbeat_thread()
        first_thread = pub._heartbeat_thread
        pub.start_heartbeat_thread()  # Should not create a new thread
        assert pub._heartbeat_thread is first_thread
        pub.stop()


class TestAgentPublisherFallback:
    def test_fallback_writes_heartbeat(self, publisher_no_valkey, tmp_fallback_dir):
        publisher_no_valkey._fallback = _FileFallback(tmp_fallback_dir)
        publisher_no_valkey.heartbeat(phase="apply", step="step-1", tokens_used=100)
        filepath = Path(tmp_fallback_dir) / "test-agent-2" / "heartbeat.jsonl"
        assert filepath.exists()
        data = json.loads(filepath.read_text().strip())
        assert data["type"] == "heartbeat"
        assert data["alive"] is True

    def test_fallback_writes_progress(self, publisher_no_valkey, tmp_fallback_dir):
        publisher_no_valkey._fallback = _FileFallback(tmp_fallback_dir)
        publisher_no_valkey.progress(tool="Read", file="test.py")
        filepath = Path(tmp_fallback_dir) / "test-agent-2" / "progress.jsonl"
        assert filepath.exists()

    def test_valkey_failure_falls_back_to_file(self, publisher_with_valkey, tmp_fallback_dir):
        pub, mock_client = publisher_with_valkey
        pub._fallback = _FileFallback(tmp_fallback_dir)
        mock_client.publish.side_effect = ConnectionError("lost connection")
        pub.heartbeat(phase="apply")
        # Should have fallen back to file
        filepath = Path(tmp_fallback_dir) / "test-agent-1" / "heartbeat.jsonl"
        assert filepath.exists()
        assert pub._use_valkey is False


# ---------------------------------------------------------------------------
# OrchestratorSubscriber Tests
# ---------------------------------------------------------------------------

@pytest.mark.timeout(10)
class TestOrchestratorSubscriberSubscriptions:
    def test_subscribe_all_creates_pattern_subscriptions(self, subscriber_with_valkey):
        sub, _, mock_pubsub = subscriber_with_valkey
        sub.subscribe_all()
        mock_pubsub.psubscribe.assert_called_once()
        patterns = mock_pubsub.psubscribe.call_args[0]
        assert "cos:agent:*:heartbeat" in patterns
        assert "cos:agent:*:progress" in patterns
        assert "cos:agent:*:question" in patterns

    def test_subscribe_agent_creates_channel_subscriptions(self, subscriber_with_valkey):
        sub, _, mock_pubsub = subscriber_with_valkey
        sub.subscribe_agent("my-agent")
        mock_pubsub.subscribe.assert_called_once()
        channels = mock_pubsub.subscribe.call_args[0]
        assert "cos:agent:my-agent:heartbeat" in channels
        assert "cos:agent:my-agent:progress" in channels


class TestOrchestratorSubscriberCallbacks:
    def test_on_heartbeat_callback_fires(self, subscriber_with_valkey):
        sub, _, _ = subscriber_with_valkey
        received = []
        sub.on_heartbeat(lambda d: received.append(d))
        sub._handle_message({"type": "heartbeat", "agent_id": "a1", "alive": True})
        assert len(received) == 1
        assert received[0]["agent_id"] == "a1"

    def test_on_progress_callback_fires(self, subscriber_with_valkey):
        sub, _, _ = subscriber_with_valkey
        received = []
        sub.on_progress(lambda d: received.append(d))
        sub._handle_message({"type": "progress", "agent_id": "a1", "tool": "Read"})
        assert len(received) == 1

    def test_on_question_callback_fires(self, subscriber_with_valkey):
        sub, _, _ = subscriber_with_valkey
        received = []
        sub.on_question(lambda d: received.append(d))
        sub._handle_message({
            "type": "question",
            "agent_id": "a1",
            "questions": ["What port?"],
        })
        assert len(received) == 1
        assert received[0]["questions"] == ["What port?"]

    def test_on_complete_callback_fires(self, subscriber_with_valkey):
        sub, _, _ = subscriber_with_valkey
        received = []
        sub.on_complete(lambda d: received.append(d))
        sub._handle_message({"type": "complete", "agent_id": "a1"})
        assert len(received) == 1

    def test_on_error_callback_fires(self, subscriber_with_valkey):
        sub, _, _ = subscriber_with_valkey
        received = []
        sub.on_error(lambda d: received.append(d))
        sub._handle_message({"type": "error", "agent_id": "a1", "error": "boom"})
        assert len(received) == 1

    def test_multiple_callbacks_same_type(self, subscriber_with_valkey):
        sub, _, _ = subscriber_with_valkey
        r1, r2 = [], []
        sub.on_heartbeat(lambda d: r1.append(d))
        sub.on_heartbeat(lambda d: r2.append(d))
        sub._handle_message({"type": "heartbeat", "agent_id": "a1"})
        assert len(r1) == 1
        assert len(r2) == 1

    def test_callback_error_does_not_crash(self, subscriber_with_valkey):
        sub, _, _ = subscriber_with_valkey

        def bad_callback(d):
            raise RuntimeError("callback crash")

        sub.on_heartbeat(bad_callback)
        # Should not raise
        sub._handle_message({"type": "heartbeat", "agent_id": "a1"})


class TestOrchestratorSubscriberAnswers:
    def test_answer_question_publishes_to_correct_channel(self, subscriber_with_valkey):
        sub, mock_client, _ = subscriber_with_valkey
        sub.answer_question("agent-1", ["yes", "port 8080"], round_num=2)
        mock_client.publish.assert_called_once()
        channel = mock_client.publish.call_args[0][0]
        assert channel == "cos:agent:agent-1:answer"
        payload = json.loads(mock_client.publish.call_args[0][1])
        assert payload["answers"] == ["yes", "port 8080"]
        assert payload["round"] == 2


class TestOrchestratorSubscriberControl:
    def test_send_control_stop(self, subscriber_with_valkey):
        sub, mock_client, _ = subscriber_with_valkey
        sub.send_control("agent-1", "stop")
        payload = json.loads(mock_client.publish.call_args[0][1])
        assert payload["command"] == "stop"
        assert "cos:agent:agent-1:control" in mock_client.publish.call_args[0][0]

    def test_send_control_pause(self, subscriber_with_valkey):
        sub, mock_client, _ = subscriber_with_valkey
        sub.send_control("agent-1", "pause")
        payload = json.loads(mock_client.publish.call_args[0][1])
        assert payload["command"] == "pause"

    def test_send_control_resume(self, subscriber_with_valkey):
        sub, mock_client, _ = subscriber_with_valkey
        sub.send_control("agent-1", "resume")
        payload = json.loads(mock_client.publish.call_args[0][1])
        assert payload["command"] == "resume"

    def test_send_control_invalid_raises(self, subscriber_with_valkey):
        sub, _, _ = subscriber_with_valkey
        with pytest.raises(ValueError, match="Invalid control command"):
            sub.send_control("agent-1", "explode")


class TestOrchestratorSubscriberActiveAgents:
    def test_get_active_agents_returns_recent(self, subscriber_with_valkey):
        sub, _, _ = subscriber_with_valkey
        now = time.time()
        sub._handle_message({
            "type": "heartbeat",
            "agent_id": "a1",
            "alive": True,
            "timestamp_epoch": now,
        })
        sub._handle_message({
            "type": "heartbeat",
            "agent_id": "a2",
            "alive": True,
            "timestamp_epoch": now - 5,
        })
        active = sub.get_active_agents(timeout_s=15)
        assert len(active) == 2

    def test_get_active_agents_excludes_old(self, subscriber_with_valkey):
        sub, _, _ = subscriber_with_valkey
        now = time.time()
        sub._handle_message({
            "type": "heartbeat",
            "agent_id": "a1",
            "alive": True,
            "timestamp_epoch": now,
        })
        sub._handle_message({
            "type": "heartbeat",
            "agent_id": "old",
            "alive": True,
            "timestamp_epoch": now - 30,
        })
        active = sub.get_active_agents(timeout_s=15)
        assert len(active) == 1
        assert active[0]["agent_id"] == "a1"

    def test_get_active_agents_excludes_dead(self, subscriber_with_valkey):
        sub, _, _ = subscriber_with_valkey
        now = time.time()
        sub._handle_message({
            "type": "heartbeat",
            "agent_id": "a1",
            "alive": False,
            "timestamp_epoch": now,
        })
        active = sub.get_active_agents(timeout_s=15)
        assert len(active) == 0

    def test_get_dead_agents_returns_old(self, subscriber_with_valkey):
        sub, _, _ = subscriber_with_valkey
        now = time.time()
        sub._handle_message({
            "type": "heartbeat",
            "agent_id": "dead-agent",
            "alive": True,
            "timestamp_epoch": now - 30,
        })
        dead = sub.get_dead_agents(timeout_s=15)
        assert len(dead) == 1
        assert dead[0]["agent_id"] == "dead-agent"

    def test_get_dead_agents_includes_alive_false(self, subscriber_with_valkey):
        sub, _, _ = subscriber_with_valkey
        now = time.time()
        sub._handle_message({
            "type": "heartbeat",
            "agent_id": "stopped",
            "alive": False,
            "timestamp_epoch": now,
        })
        dead = sub.get_dead_agents(timeout_s=15)
        assert len(dead) == 1


@pytest.mark.timeout(10)
class TestOrchestratorSubscriberIterEvents:
    def test_iter_events_yields_messages(self, subscriber_with_valkey):
        sub, _, mock_pubsub = subscriber_with_valkey
        sub.subscribe_all()

        # Simulate messages then None
        messages = [
            {
                "type": "pmessage",
                "data": json.dumps({"type": "heartbeat", "agent_id": "a1", "alive": True}),
            },
            {
                "type": "pmessage",
                "data": json.dumps({"type": "progress", "agent_id": "a1", "tool": "Read"}),
            },
            None,  # Will cause timeout exit
        ]
        mock_pubsub.get_message.side_effect = messages

        events = list(sub.iter_events(timeout=0.1))
        # Should get at least 1 event before timeout
        assert len(events) >= 1


# ---------------------------------------------------------------------------
# Integration Tests (mocked Valkey)
# ---------------------------------------------------------------------------

@pytest.mark.timeout(10)
class TestIntegrationPublisherSubscriber:
    def test_heartbeat_flow(self, tmp_fallback_dir):
        """Publisher heartbeat -> Subscriber receives via handle_message."""
        mock_redis = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        published = []

        def capture_publish(channel, data):
            published.append((channel, data))
            return 1

        mock_client.publish.side_effect = capture_publish
        mock_redis.Redis.from_url.return_value = mock_client

        with patch.dict("sys.modules", {"redis": mock_redis}):
            pub = AgentPublisher("flow-agent", fallback_dir=tmp_fallback_dir)
            pub._use_valkey = True
            pub._client = mock_client

            sub = OrchestratorSubscriber(fallback_dir=tmp_fallback_dir)
            sub._use_valkey = True
            sub._client = mock_client

        received_heartbeats = []
        sub.on_heartbeat(lambda d: received_heartbeats.append(d))

        # Publisher sends heartbeat
        pub.heartbeat(phase="apply", step="step-1")

        # Simulate subscriber receiving the published message
        assert len(published) == 1
        channel, payload = published[0]
        data = json.loads(payload)
        sub._handle_message(data)

        assert len(received_heartbeats) == 1
        assert received_heartbeats[0]["phase"] == "apply"
        assert received_heartbeats[0]["agent_id"] == "flow-agent"

    def test_question_answer_flow(self, tmp_fallback_dir):
        """Publisher asks question -> Subscriber answers -> via file fallback."""
        pub = AgentPublisher.__new__(AgentPublisher)
        pub.agent_id = "qa-agent"
        pub.valkey_url = "redis://localhost:6379"
        pub._fallback = _FileFallback(tmp_fallback_dir)
        pub._client = None
        pub._pubsub = None
        pub._heartbeat_thread = None
        pub._heartbeat_stop = threading.Event()
        pub._lock = threading.Lock()
        pub._phase = "unknown"
        pub._step = ""
        pub._tokens_used = 0
        pub._use_valkey = False

        sub = OrchestratorSubscriber.__new__(OrchestratorSubscriber)
        sub.valkey_url = "redis://localhost:6379"
        sub._fallback = _FileFallback(tmp_fallback_dir)
        sub._client = None
        sub._pubsub = None
        sub._use_valkey = False
        sub._callbacks = {"heartbeat": [], "progress": [], "question": [], "complete": [], "error": []}
        sub._agent_heartbeats = {}
        sub._lock = threading.Lock()
        sub._listener_thread = None
        sub._listener_stop = threading.Event()

        # Subscriber answers in a background thread
        def answer_later():
            time.sleep(0.5)
            sub.answer_question("qa-agent", ["port 8080", "use Valkey"], round_num=1)

        t = threading.Thread(target=answer_later, daemon=True)
        t.start()

        # Publisher asks and waits
        answers = pub.ask_clarification(["What port?", "Which cache?"], round_num=1, timeout=3)
        t.join(timeout=5)

        assert answers == ["port 8080", "use Valkey"]

    def test_progress_callback_flow(self, tmp_fallback_dir):
        """Publisher progress -> Subscriber callback fires."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        published = []
        mock_client.publish.side_effect = lambda ch, d: published.append((ch, d)) or 1

        sub = OrchestratorSubscriber.__new__(OrchestratorSubscriber)
        sub._use_valkey = True
        sub._client = mock_client
        sub._pubsub = MagicMock()
        sub._callbacks = {"heartbeat": [], "progress": [], "question": [], "complete": [], "error": []}
        sub._agent_heartbeats = {}
        sub._lock = threading.Lock()
        sub._listener_thread = None
        sub._listener_stop = threading.Event()
        sub._fallback = _FileFallback(tmp_fallback_dir)
        sub.valkey_url = "redis://localhost:6379"

        received = []
        sub.on_progress(lambda d: received.append(d))

        pub = AgentPublisher.__new__(AgentPublisher)
        pub.agent_id = "prog-agent"
        pub.valkey_url = "redis://localhost:6379"
        pub._fallback = _FileFallback(tmp_fallback_dir)
        pub._client = mock_client
        pub._pubsub = None
        pub._heartbeat_thread = None
        pub._heartbeat_stop = threading.Event()
        pub._lock = threading.Lock()
        pub._phase = "apply"
        pub._step = ""
        pub._tokens_used = 0
        pub._use_valkey = True

        pub.progress(tool="Edit", file="main.go", action="add handler", step_current=1, step_total=5)

        assert len(published) == 1
        data = json.loads(published[0][1])
        sub._handle_message(data)
        assert len(received) == 1
        assert received[0]["tool"] == "Edit"

    def test_multiple_agents_all_received(self, tmp_fallback_dir):
        """3 publishers, 1 subscriber, all events received."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        published = []
        mock_client.publish.side_effect = lambda ch, d: published.append((ch, d)) or 1

        sub = OrchestratorSubscriber.__new__(OrchestratorSubscriber)
        sub._use_valkey = True
        sub._client = mock_client
        sub._pubsub = MagicMock()
        sub._callbacks = {"heartbeat": [], "progress": [], "question": [], "complete": [], "error": []}
        sub._agent_heartbeats = {}
        sub._lock = threading.Lock()
        sub._listener_thread = None
        sub._listener_stop = threading.Event()
        sub._fallback = _FileFallback(tmp_fallback_dir)
        sub.valkey_url = "redis://localhost:6379"

        received = []
        sub.on_heartbeat(lambda d: received.append(d))

        # Create 3 publishers
        for i in range(3):
            pub = AgentPublisher.__new__(AgentPublisher)
            pub.agent_id = "agent-%d" % i
            pub.valkey_url = "redis://localhost:6379"
            pub._fallback = _FileFallback(tmp_fallback_dir)
            pub._client = mock_client
            pub._pubsub = None
            pub._heartbeat_thread = None
            pub._heartbeat_stop = threading.Event()
            pub._lock = threading.Lock()
            pub._phase = "phase-%d" % i
            pub._step = ""
            pub._tokens_used = 0
            pub._use_valkey = True
            pub.heartbeat()

        assert len(published) == 3

        for ch, payload in published:
            data = json.loads(payload)
            sub._handle_message(data)

        assert len(received) == 3
        agent_ids = {r["agent_id"] for r in received}
        assert agent_ids == {"agent-0", "agent-1", "agent-2"}

    def test_agent_dies_subscriber_detects(self, tmp_fallback_dir):
        """Agent heartbeat stops -> subscriber detects dead agent."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.publish.return_value = 1

        sub = OrchestratorSubscriber.__new__(OrchestratorSubscriber)
        sub._use_valkey = True
        sub._client = mock_client
        sub._pubsub = MagicMock()
        sub._callbacks = {"heartbeat": [], "progress": [], "question": [], "complete": [], "error": []}
        sub._agent_heartbeats = {}
        sub._lock = threading.Lock()
        sub._listener_thread = None
        sub._listener_stop = threading.Event()
        sub._fallback = _FileFallback(tmp_fallback_dir)
        sub.valkey_url = "redis://localhost:6379"

        # Agent sends heartbeat long ago
        sub._handle_message({
            "type": "heartbeat",
            "agent_id": "dying-agent",
            "alive": True,
            "timestamp_epoch": time.time() - 30,
        })

        dead = sub.get_dead_agents(timeout_s=15)
        assert len(dead) == 1
        assert dead[0]["agent_id"] == "dying-agent"

    def test_graceful_degradation_file_fallback(self, tmp_fallback_dir):
        """Valkey down -> file fallback -> events still logged."""
        pub = AgentPublisher.__new__(AgentPublisher)
        pub.agent_id = "fallback-agent"
        pub.valkey_url = "redis://localhost:6379"
        pub._fallback = _FileFallback(tmp_fallback_dir)
        pub._client = None
        pub._pubsub = None
        pub._heartbeat_thread = None
        pub._heartbeat_stop = threading.Event()
        pub._lock = threading.Lock()
        pub._phase = "apply"
        pub._step = ""
        pub._tokens_used = 0
        pub._use_valkey = False

        pub.heartbeat(phase="apply", step="step-1")
        pub.progress(tool="Read", file="main.go")
        pub.report_error("something broke")

        fb = _FileFallback(tmp_fallback_dir)
        hb_events = fb.read_events("fallback-agent", "heartbeat")
        assert len(hb_events) == 1
        prog_events = fb.read_events("fallback-agent", "progress")
        assert len(prog_events) == 2  # progress + error

    def test_control_flow_stop(self, subscriber_with_valkey):
        """Orchestrator sends stop -> publishes to control channel."""
        sub, mock_client, _ = subscriber_with_valkey
        sub.send_control("target-agent", "stop")
        channel = mock_client.publish.call_args[0][0]
        assert channel == "cos:agent:target-agent:control"
        payload = json.loads(mock_client.publish.call_args[0][1])
        assert payload["command"] == "stop"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

@pytest.mark.timeout(10)
class TestEdgeCases:
    def test_large_message_truncated(self, publisher_with_valkey):
        """Messages exceeding MAX_MESSAGE_BYTES get truncated."""
        pub, mock_client = publisher_with_valkey
        large_content = "x" * (MAX_MESSAGE_BYTES + 1000)
        pub._publish("progress", {"type": "progress", "content": large_content})
        payload = json.loads(mock_client.publish.call_args[0][1])
        # Content should be truncated
        assert len(payload.get("content", "")) < MAX_MESSAGE_BYTES

    def test_concurrent_publishers_thread_safe(self, tmp_fallback_dir):
        """Multiple threads publishing simultaneously."""
        fb = _FileFallback(tmp_fallback_dir)
        errors = []

        def publish_many(agent_id, count):
            try:
                for i in range(count):
                    fb.publish(
                        "cos:agent:%s:heartbeat" % agent_id,
                        {"n": i, "timestamp_epoch": time.time()},
                    )
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=publish_many, args=("agent-%d" % i, 20), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0

        # Verify all events were written
        for i in range(5):
            events = fb.read_events("agent-%d" % i, "heartbeat")
            assert len(events) == 20

    def test_channel_name_sanitization_special_chars(self):
        """Agent IDs with special chars are sanitized in channel names."""
        # The channel format is "cos:agent:{sanitized_id}:{suffix}" so structural
        # colons are expected.  We verify that the special chars in the AGENT NAME
        # portion are replaced with '_'.
        ch = _channel("bad:agent", "heartbeat")
        assert "bad_agent" in ch  # colon in agent name replaced
        assert "/" not in _channel("path/agent", "heartbeat")
        assert " " not in _channel("space agent", "heartbeat")
        assert "!" not in _channel("bang!", "heartbeat")

    def test_subscriber_stop_cleanup(self, subscriber_with_valkey):
        """Subscriber stop cleans up resources."""
        sub, mock_client, mock_pubsub = subscriber_with_valkey
        sub.stop()
        mock_pubsub.unsubscribe.assert_called()
        mock_pubsub.punsubscribe.assert_called()
        mock_pubsub.close.assert_called()
        mock_client.close.assert_called()

    def test_publisher_no_crash_when_valkey_disconnects(self, publisher_with_valkey, tmp_fallback_dir):
        """Publisher gracefully handles mid-session Valkey disconnect."""
        pub, mock_client = publisher_with_valkey
        pub._fallback = _FileFallback(tmp_fallback_dir)

        # First call works
        pub.heartbeat(phase="apply")
        assert mock_client.publish.call_count == 1

        # Valkey goes down
        mock_client.publish.side_effect = ConnectionError("connection lost")
        pub._use_valkey = True  # Reset so it tries Valkey first
        pub.heartbeat(phase="verify")

        # Should have fallen back to file
        assert pub._use_valkey is False
        filepath = Path(tmp_fallback_dir) / "test-agent-1" / "heartbeat.jsonl"
        assert filepath.exists()

    def test_answer_question_file_fallback(self, subscriber_with_valkey, tmp_fallback_dir):
        """Answer question falls back to file when Valkey publish fails."""
        sub, mock_client, _ = subscriber_with_valkey
        sub._fallback = _FileFallback(tmp_fallback_dir)
        mock_client.publish.side_effect = ConnectionError("lost")
        sub.answer_question("agent-1", ["answer1"], round_num=1)
        # Should have written to file
        events = sub._fallback.read_events("agent-1", "answer")
        assert len(events) == 1
        assert events[0]["answers"] == ["answer1"]

    def test_valid_control_commands_constant(self):
        """Verify the set of valid control commands."""
        assert VALID_CONTROL_COMMANDS == {"stop", "pause", "resume"}

    def test_heartbeat_constants(self):
        """Verify heartbeat timing constants."""
        assert HEARTBEAT_INTERVAL_S == 5
        assert HEARTBEAT_TIMEOUT_S == 15


# ---------------------------------------------------------------------------
# Smart Infra Integration Tests
# ---------------------------------------------------------------------------


class TestSmartInfraIntegration:
    """Tests for agent_bus smart_infra integration (on-demand Valkey)."""

    def test_ensure_valkey_called_on_publisher_connect_failure(self, tmp_fallback_dir):
        """AgentPublisher calls ensure_service('valkey') when initial connect fails."""
        mock_redis_cls = MagicMock()
        mock_client = MagicMock()
        # First ping fails (not running), second ping succeeds (after smart_infra)
        mock_client.ping.side_effect = [ConnectionError("refused"), True]
        mock_redis_cls.from_url.return_value = mock_client

        with patch.dict("sys.modules", {"redis": MagicMock(Redis=mock_redis_cls)}), \
             patch("lib.agent_bus._ensure_valkey_via_smart_infra", return_value=True) as mock_ensure:
            pub = AgentPublisher("test-agent", fallback_dir=tmp_fallback_dir)
            mock_ensure.assert_called_once()
            assert pub._use_valkey is True

    def test_ensure_valkey_not_called_when_already_connected(self, tmp_fallback_dir):
        """AgentPublisher does NOT call ensure_service when Valkey connects on first try."""
        mock_redis_cls = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis_cls.from_url.return_value = mock_client

        with patch.dict("sys.modules", {"redis": MagicMock(Redis=mock_redis_cls)}), \
             patch("lib.agent_bus._ensure_valkey_via_smart_infra") as mock_ensure:
            pub = AgentPublisher("test-agent", fallback_dir=tmp_fallback_dir)
            mock_ensure.assert_not_called()
            assert pub._use_valkey is True

    def test_fallback_when_smart_infra_fails(self, tmp_fallback_dir):
        """AgentPublisher falls back to file when both Valkey and smart_infra fail."""
        mock_redis_cls = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("refused")
        mock_redis_cls.from_url.return_value = mock_client

        with patch.dict("sys.modules", {"redis": MagicMock(Redis=mock_redis_cls)}), \
             patch("lib.agent_bus._ensure_valkey_via_smart_infra", return_value=False):
            pub = AgentPublisher("test-agent", fallback_dir=tmp_fallback_dir)
            assert pub._use_valkey is False

    def test_orchestrator_subscriber_calls_ensure_on_failure(self, tmp_fallback_dir):
        """OrchestratorSubscriber calls ensure_service('valkey') when initial connect fails."""
        mock_redis_cls = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.side_effect = [ConnectionError("refused"), True]
        mock_client.pubsub.return_value = MagicMock()
        mock_redis_cls.from_url.return_value = mock_client

        with patch.dict("sys.modules", {"redis": MagicMock(Redis=mock_redis_cls)}), \
             patch("lib.agent_bus._ensure_valkey_via_smart_infra", return_value=True) as mock_ensure:
            sub = OrchestratorSubscriber(fallback_dir=tmp_fallback_dir)
            mock_ensure.assert_called_once()
            assert sub._use_valkey is True

    def test_is_valkey_available_tries_smart_infra(self):
        """is_valkey_available() tries smart_infra when Valkey is not reachable."""
        mock_redis_mod = MagicMock()
        mock_client = MagicMock()
        # First ping fails, second succeeds after smart_infra
        mock_client.ping.side_effect = [ConnectionError("refused"), True]
        mock_redis_mod.Redis.from_url.return_value = mock_client

        with patch.dict("sys.modules", {"redis": mock_redis_mod}), \
             patch("lib.agent_bus._ensure_valkey_via_smart_infra", return_value=True) as mock_ensure:
            result = is_valkey_available()
            mock_ensure.assert_called_once()
            assert result is True

    def test_ensure_valkey_via_smart_infra_graceful_on_import_error(self):
        """_ensure_valkey_via_smart_infra returns False on import error."""
        from lib.agent_bus import _ensure_valkey_via_smart_infra

        with patch("lib.agent_bus.ensure_service", side_effect=ImportError("no module")):
            # Should not raise -- returns False
            pass

        # Test with the actual function patching smart_infra
        with patch.dict("sys.modules", {"lib.smart_infra": None}):
            result = _ensure_valkey_via_smart_infra()
            assert result is False
