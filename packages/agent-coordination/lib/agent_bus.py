# scope: both
"""Cognitive OS Agent Communication Bus -- Valkey pub/sub for real-time agent coordination.

Provides bidirectional communication between agents and the orchestrator using
Redis-compatible (Valkey) pub/sub channels. Falls back to file-based signaling
when Valkey is unavailable.

Channels:
    cos:agent:{id}:heartbeat  -- agent publishes every 5s
    cos:agent:{id}:progress   -- agent publishes on each tool use
    cos:agent:{id}:question   -- agent publishes NEEDS_CLARIFICATION questions
    cos:agent:{id}:answer     -- orchestrator publishes answers to questions
    cos:agent:{id}:control    -- orchestrator sends commands (stop, pause, resume)
    cos:agent:*:heartbeat     -- orchestrator subscribes to ALL heartbeats

Python 3.9+ compatible.
"""

import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

# Default file-based fallback directory
_DEFAULT_FALLBACK_DIR = ".cognitive-os/agent-bus"

# Channel prefix
_CHANNEL_PREFIX = "cos:agent"

# Heartbeat interval and timeout
HEARTBEAT_INTERVAL_S = 5
HEARTBEAT_TIMEOUT_S = 15

# Default clarification timeout
CLARIFICATION_TIMEOUT_S = 300

# Max message size for safety
MAX_MESSAGE_BYTES = 256 * 1024  # 256KB

# Valid control commands
VALID_CONTROL_COMMANDS = frozenset({"stop", "pause", "resume"})


def _sanitize_agent_id(agent_id: str) -> str:
    """Sanitize agent_id for use in channel names.

    Removes characters that could break channel patterns or cause injection.
    Allows alphanumeric, hyphens, underscores, and dots.
    """
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", agent_id)
    if not sanitized:
        sanitized = "unknown"
    return sanitized


def _channel(agent_id: str, suffix: str) -> str:
    """Build a channel name for a given agent and suffix."""
    safe_id = _sanitize_agent_id(agent_id)
    return "%s:%s:%s" % (_CHANNEL_PREFIX, safe_id, suffix)


def _pattern_channel(suffix: str) -> str:
    """Build a pattern channel for subscribing to all agents."""
    return "%s:*:%s" % (_CHANNEL_PREFIX, suffix)


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _now_epoch() -> float:
    """Return current time as epoch float."""
    return time.time()


def _ensure_valkey_via_smart_infra() -> bool:
    """Attempt to start the Valkey service via smart_infra.

    Returns True if the service was ensured successfully, False otherwise.
    This is a best-effort operation that never raises.
    """
    try:
        from lib.smart_infra import ensure_service

        return ensure_service("valkey")
    except Exception as exc:
        logger.debug("smart_infra.ensure_service('valkey') failed: %s", exc)
        return False


def is_valkey_available(valkey_url: str = "redis://localhost:6379") -> bool:
    """Check if Valkey/Redis is reachable.

    If not reachable on first try, attempts to start Valkey via
    smart_infra on-demand infrastructure and retries once.

    Args:
        valkey_url: Redis-compatible connection URL.

    Returns:
        True if a PING succeeds, False otherwise.
    """
    try:
        import redis

        client = redis.Redis.from_url(valkey_url, socket_connect_timeout=2)
        if client.ping():
            return True
    except Exception:
        pass

    # Valkey not reachable -- try starting it via smart_infra
    if _ensure_valkey_via_smart_infra():
        try:
            import redis

            client = redis.Redis.from_url(valkey_url, socket_connect_timeout=2)
            return client.ping()
        except Exception:
            pass

    return False


class _FileFallback:
    """File-based fallback when Valkey is unavailable.

    Writes events as JSONL to .cognitive-os/agent-bus/{agent_id}/{channel}.jsonl
    """

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)

    def publish(self, channel: str, data: Dict[str, Any]) -> None:
        """Append an event to the channel's JSONL file."""
        # Extract agent_id from channel: cos:agent:{id}:{suffix}
        parts = channel.split(":")
        if len(parts) >= 4:
            agent_id = parts[2]
            suffix = parts[3]
        else:
            agent_id = "unknown"
            suffix = channel

        agent_dir = self.base_dir / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        filepath = agent_dir / ("%s.jsonl" % suffix)
        line = json.dumps(data, default=str)
        with open(filepath, "a") as f:
            f.write(line + "\n")

    def read_events(
        self, agent_id: str, suffix: str, since_epoch: float = 0
    ) -> List[Dict[str, Any]]:
        """Read events from a channel's JSONL file, optionally filtered by time."""
        filepath = self.base_dir / agent_id / ("%s.jsonl" % suffix)
        events: List[Dict[str, Any]] = []
        if not filepath.exists():
            return events
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    ts = event.get("timestamp_epoch", 0)
                    if ts >= since_epoch:
                        events.append(event)
                except (json.JSONDecodeError, ValueError):
                    continue
        return events


class AgentPublisher:
    """Publisher used by agents to send heartbeats, progress, and questions.

    Args:
        agent_id: Unique identifier for this agent.
        valkey_url: Redis-compatible connection URL.
        fallback_dir: Directory for file-based fallback. Defaults to
            .cognitive-os/agent-bus relative to cwd.
    """

    def __init__(
        self,
        agent_id: str,
        valkey_url: str = "redis://localhost:6379",
        fallback_dir: Optional[str] = None,
    ) -> None:
        self.agent_id = _sanitize_agent_id(agent_id)
        self.valkey_url = valkey_url
        self._fallback = _FileFallback(fallback_dir or _DEFAULT_FALLBACK_DIR)
        self._client: Any = None
        self._pubsub: Any = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_stop = threading.Event()
        self._lock = threading.Lock()
        self._phase = "unknown"
        self._step = ""
        self._tokens_used = 0
        self._use_valkey = False

        self._connect()

    def _connect(self) -> None:
        """Attempt to connect to Valkey. Falls back to file if unavailable.

        On first failure, tries to start Valkey via smart_infra on-demand
        infrastructure before falling back to file-based signaling.
        """
        try:
            import redis

            self._client = redis.Redis.from_url(
                self.valkey_url, socket_connect_timeout=2, decode_responses=True
            )
            self._client.ping()
            self._use_valkey = True
            logger.debug("AgentPublisher(%s): connected to Valkey", self.agent_id)
            return
        except Exception:
            pass

        # Try starting Valkey via smart_infra before giving up
        if _ensure_valkey_via_smart_infra():
            try:
                import redis

                self._client = redis.Redis.from_url(
                    self.valkey_url, socket_connect_timeout=2, decode_responses=True
                )
                self._client.ping()
                self._use_valkey = True
                logger.debug(
                    "AgentPublisher(%s): connected to Valkey after smart_infra start",
                    self.agent_id,
                )
                return
            except Exception as e:
                logger.warning(
                    "AgentPublisher(%s): Valkey still unavailable after smart_infra (%s)",
                    self.agent_id,
                    e,
                )

        self._use_valkey = False
        self._client = None
        logger.warning(
            "AgentPublisher(%s): Valkey unavailable, using file fallback",
            self.agent_id,
        )

    def _publish(self, suffix: str, data: Dict[str, Any]) -> None:
        """Publish a message to the agent's channel."""
        data["agent_id"] = self.agent_id
        data["timestamp"] = _now_iso()
        data["timestamp_epoch"] = _now_epoch()

        channel = _channel(self.agent_id, suffix)

        # Check message size
        payload = json.dumps(data, default=str)
        if len(payload.encode("utf-8")) > MAX_MESSAGE_BYTES:
            logger.warning(
                "Message exceeds %d bytes, truncating content", MAX_MESSAGE_BYTES
            )
            if "content" in data:
                data["content"] = str(data["content"])[:10000] + "...[truncated]"
                payload = json.dumps(data, default=str)

        if self._use_valkey and self._client is not None:
            try:
                self._client.publish(channel, payload)
                return
            except Exception as e:
                logger.warning("Valkey publish failed (%s), falling back to file", e)
                self._use_valkey = False

        # File fallback
        self._fallback.publish(channel, data)

    def heartbeat(self, phase: str = "", step: str = "", tokens_used: int = 0) -> None:
        """Publish a heartbeat message.

        Args:
            phase: Current agent phase (e.g., 'apply', 'verify').
            step: Current step description.
            tokens_used: Cumulative tokens used.
        """
        with self._lock:
            if phase:
                self._phase = phase
            if step:
                self._step = step
            if tokens_used:
                self._tokens_used = tokens_used

        self._publish(
            "heartbeat",
            {
                "type": "heartbeat",
                "phase": self._phase,
                "step": self._step,
                "tokens_used": self._tokens_used,
                "alive": True,
            },
        )

    def progress(
        self,
        tool: str,
        file: str = "",
        action: str = "",
        step_current: int = 0,
        step_total: int = 0,
    ) -> None:
        """Publish a progress event for a tool use.

        Args:
            tool: Name of the tool being used.
            file: File being operated on.
            action: Description of the action.
            step_current: Current step number.
            step_total: Total number of steps.
        """
        self._publish(
            "progress",
            {
                "type": "progress",
                "tool": tool,
                "file": file,
                "action": action,
                "step_current": step_current,
                "step_total": step_total,
            },
        )

    def ask_clarification(
        self,
        questions: List[str],
        round_num: int = 1,
        timeout: int = CLARIFICATION_TIMEOUT_S,
    ) -> List[str]:
        """Publish questions and block waiting for answers.

        Args:
            questions: List of questions to ask.
            round_num: Clarification round number.
            timeout: Seconds to wait for answer before returning empty.

        Returns:
            List of answers, or empty list on timeout.
        """
        if not questions:
            return []

        self._publish(
            "question",
            {
                "type": "question",
                "questions": questions,
                "round": round_num,
            },
        )

        # Wait for answer on the answer channel
        answer_channel = _channel(self.agent_id, "answer")

        if self._use_valkey and self._client is not None:
            try:
                import redis

                # Create a separate client for subscribing (blocking)
                sub_client = redis.Redis.from_url(
                    self.valkey_url,
                    socket_connect_timeout=2,
                    decode_responses=True,
                )
                pubsub = sub_client.pubsub()
                pubsub.subscribe(answer_channel)

                deadline = time.time() + timeout
                while time.time() < deadline:
                    message = pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if message and message.get("type") == "message":
                        try:
                            data = json.loads(message["data"])
                            answers = data.get("answers", [])
                            pubsub.unsubscribe()
                            pubsub.close()
                            sub_client.close()
                            return answers
                        except (json.JSONDecodeError, ValueError):
                            continue

                pubsub.unsubscribe()
                pubsub.close()
                sub_client.close()
                logger.warning("Clarification timeout after %ds", timeout)
                return []
            except Exception as e:
                logger.warning("Valkey subscribe failed (%s)", e)

        # File fallback: poll for answer file
        deadline = time.time() + timeout
        while time.time() < deadline:
            events = self._fallback.read_events(self.agent_id, "answer")
            for event in reversed(events):
                if event.get("type") == "answer" and event.get("round") == round_num:
                    return event.get("answers", [])
            time.sleep(1.0)

        logger.warning("Clarification timeout (file fallback) after %ds", timeout)
        return []

    def report_complete(self, result_summary: str) -> None:
        """Publish a completion event.

        Args:
            result_summary: Summary of the completed work.
        """
        self._publish(
            "progress",
            {
                "type": "complete",
                "result_summary": result_summary,
            },
        )
        # Send final heartbeat with alive=False
        self._publish(
            "heartbeat",
            {
                "type": "heartbeat",
                "phase": self._phase,
                "step": "complete",
                "tokens_used": self._tokens_used,
                "alive": False,
            },
        )

    def report_error(self, error: str) -> None:
        """Publish an error event.

        Args:
            error: Error message or description.
        """
        self._publish(
            "progress",
            {
                "type": "error",
                "error": error,
            },
        )

    def start_heartbeat_thread(self) -> None:
        """Start a background thread that sends heartbeat every 5 seconds."""
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return

        self._heartbeat_stop.clear()

        def _heartbeat_loop() -> None:
            while not self._heartbeat_stop.is_set():
                try:
                    self.heartbeat()
                except Exception as e:
                    logger.debug("Heartbeat error: %s", e)
                self._heartbeat_stop.wait(HEARTBEAT_INTERVAL_S)

        self._heartbeat_thread = threading.Thread(
            target=_heartbeat_loop, daemon=True, name="agent-heartbeat-%s" % self.agent_id
        )
        self._heartbeat_thread.start()
        logger.debug("Heartbeat thread started for agent %s", self.agent_id)

    def stop(self) -> None:
        """Stop heartbeat thread and publish final alive=false heartbeat."""
        self._heartbeat_stop.set()
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=2)
            self._heartbeat_thread = None

        # Publish final dead heartbeat
        self._publish(
            "heartbeat",
            {
                "type": "heartbeat",
                "phase": self._phase,
                "step": "stopped",
                "tokens_used": self._tokens_used,
                "alive": False,
            },
        )
        logger.debug("Agent %s stopped", self.agent_id)


class OrchestratorSubscriber:
    """Subscriber used by the orchestrator to monitor agents.

    Args:
        valkey_url: Redis-compatible connection URL.
        fallback_dir: Directory for file-based fallback.
    """

    def __init__(
        self,
        valkey_url: str = "redis://localhost:6379",
        fallback_dir: Optional[str] = None,
    ) -> None:
        self.valkey_url = valkey_url
        self._fallback = _FileFallback(fallback_dir or _DEFAULT_FALLBACK_DIR)
        self._client: Any = None
        self._pubsub: Any = None
        self._use_valkey = False
        self._callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {
            "heartbeat": [],
            "progress": [],
            "question": [],
            "complete": [],
            "error": [],
        }
        self._agent_heartbeats: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._listener_thread: Optional[threading.Thread] = None
        self._listener_stop = threading.Event()

        self._connect()

    def _connect(self) -> None:
        """Attempt to connect to Valkey.

        On first failure, tries to start Valkey via smart_infra on-demand
        infrastructure before falling back to file-based signaling.
        """
        try:
            import redis

            self._client = redis.Redis.from_url(
                self.valkey_url, socket_connect_timeout=2, decode_responses=True
            )
            self._client.ping()
            self._pubsub = self._client.pubsub()
            self._use_valkey = True
            logger.debug("OrchestratorSubscriber: connected to Valkey")
            return
        except Exception:
            pass

        # Try starting Valkey via smart_infra before giving up
        if _ensure_valkey_via_smart_infra():
            try:
                import redis

                self._client = redis.Redis.from_url(
                    self.valkey_url, socket_connect_timeout=2, decode_responses=True
                )
                self._client.ping()
                self._pubsub = self._client.pubsub()
                self._use_valkey = True
                logger.debug(
                    "OrchestratorSubscriber: connected to Valkey after smart_infra start"
                )
                return
            except Exception as e:
                logger.warning(
                    "OrchestratorSubscriber: Valkey still unavailable after smart_infra (%s)",
                    e,
                )

        self._use_valkey = False
        self._client = None
        self._pubsub = None
        logger.warning(
            "OrchestratorSubscriber: Valkey unavailable, using file fallback"
        )

    def _handle_message(self, data: Dict[str, Any]) -> None:
        """Route a message to registered callbacks."""
        msg_type = data.get("type", "")
        agent_id = data.get("agent_id", "")

        # Track heartbeats
        if msg_type == "heartbeat":
            with self._lock:
                self._agent_heartbeats[agent_id] = data

        # Fire callbacks
        callbacks = self._callbacks.get(msg_type, [])
        for cb in callbacks:
            try:
                cb(data)
            except Exception as e:
                logger.error("Callback error for %s: %s", msg_type, e)

    def subscribe_all(self) -> None:
        """Subscribe to all agent channels using pattern subscription."""
        if self._use_valkey and self._pubsub is not None:
            patterns = [
                _pattern_channel("heartbeat"),
                _pattern_channel("progress"),
                _pattern_channel("question"),
            ]
            self._pubsub.psubscribe(*patterns)
            self._start_listener()
        else:
            logger.info("subscribe_all: no Valkey, file fallback active")

    def subscribe_agent(self, agent_id: str) -> None:
        """Subscribe to a specific agent's channels.

        Args:
            agent_id: Agent to subscribe to.
        """
        safe_id = _sanitize_agent_id(agent_id)
        if self._use_valkey and self._pubsub is not None:
            channels = [
                _channel(safe_id, "heartbeat"),
                _channel(safe_id, "progress"),
                _channel(safe_id, "question"),
            ]
            self._pubsub.subscribe(*channels)
            self._start_listener()
        else:
            logger.info("subscribe_agent(%s): no Valkey, file fallback active", agent_id)

    def _start_listener(self) -> None:
        """Start background listener thread if not already running."""
        if self._listener_thread is not None and self._listener_thread.is_alive():
            return

        self._listener_stop.clear()

        def _listen() -> None:
            while not self._listener_stop.is_set():
                if self._pubsub is None:
                    break
                try:
                    message = self._pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if message and message.get("type") in ("message", "pmessage"):
                        raw = message.get("data", "")
                        if isinstance(raw, str):
                            try:
                                data = json.loads(raw)
                                self._handle_message(data)
                            except (json.JSONDecodeError, ValueError):
                                pass
                except Exception as e:
                    logger.debug("Listener error: %s", e)
                    time.sleep(1)

        self._listener_thread = threading.Thread(
            target=_listen, daemon=True, name="orchestrator-listener"
        )
        self._listener_thread.start()

    def on_heartbeat(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for heartbeat events.

        Args:
            callback: Function called with heartbeat data dict.
        """
        self._callbacks["heartbeat"].append(callback)

    def on_progress(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for progress events.

        Args:
            callback: Function called with progress data dict.
        """
        self._callbacks["progress"].append(callback)

    def on_question(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for question events.

        Args:
            callback: Function called with question data dict.
        """
        self._callbacks["question"].append(callback)

    def on_complete(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for completion events.

        Args:
            callback: Function called with completion data dict.
        """
        self._callbacks["complete"].append(callback)

    def on_error(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for error events.

        Args:
            callback: Function called with error data dict.
        """
        self._callbacks["error"].append(callback)

    def answer_question(self, agent_id: str, answers: List[str], round_num: int = 1) -> None:
        """Publish answers to an agent's questions.

        Args:
            agent_id: Target agent.
            answers: List of answer strings.
            round_num: Which clarification round this answers.
        """
        safe_id = _sanitize_agent_id(agent_id)
        channel = _channel(safe_id, "answer")
        data = {
            "type": "answer",
            "agent_id": safe_id,
            "answers": answers,
            "round": round_num,
            "timestamp": _now_iso(),
            "timestamp_epoch": _now_epoch(),
        }
        payload = json.dumps(data, default=str)

        if self._use_valkey and self._client is not None:
            try:
                self._client.publish(channel, payload)
                return
            except Exception as e:
                logger.warning("Valkey publish answer failed (%s)", e)

        # File fallback
        self._fallback.publish(channel, data)

    def send_control(self, agent_id: str, command: str) -> None:
        """Send a control command to an agent.

        Args:
            agent_id: Target agent.
            command: One of 'stop', 'pause', 'resume'.

        Raises:
            ValueError: If command is not valid.
        """
        if command not in VALID_CONTROL_COMMANDS:
            raise ValueError(
                "Invalid control command '%s'. Must be one of: %s"
                % (command, ", ".join(sorted(VALID_CONTROL_COMMANDS)))
            )

        safe_id = _sanitize_agent_id(agent_id)
        channel = _channel(safe_id, "control")
        data = {
            "type": "control",
            "agent_id": safe_id,
            "command": command,
            "timestamp": _now_iso(),
            "timestamp_epoch": _now_epoch(),
        }
        payload = json.dumps(data, default=str)

        if self._use_valkey and self._client is not None:
            try:
                self._client.publish(channel, payload)
                return
            except Exception as e:
                logger.warning("Valkey publish control failed (%s)", e)

        # File fallback
        self._fallback.publish(channel, data)

    def get_active_agents(self, timeout_s: int = HEARTBEAT_TIMEOUT_S) -> List[Dict[str, Any]]:
        """Return agents that have sent a heartbeat within the timeout.

        Args:
            timeout_s: Seconds since last heartbeat to consider active.

        Returns:
            List of heartbeat data dicts for active agents.
        """
        cutoff = _now_epoch() - timeout_s
        active: List[Dict[str, Any]] = []
        with self._lock:
            for agent_id, hb in self._agent_heartbeats.items():
                ts = hb.get("timestamp_epoch", 0)
                if ts >= cutoff and hb.get("alive", False):
                    active.append(hb)
        return active

    def get_dead_agents(self, timeout_s: int = HEARTBEAT_TIMEOUT_S) -> List[Dict[str, Any]]:
        """Return agents whose heartbeat is older than timeout or marked dead.

        Args:
            timeout_s: Seconds since last heartbeat to consider dead.

        Returns:
            List of heartbeat data dicts for dead agents.
        """
        cutoff = _now_epoch() - timeout_s
        dead: List[Dict[str, Any]] = []
        with self._lock:
            for agent_id, hb in self._agent_heartbeats.items():
                ts = hb.get("timestamp_epoch", 0)
                if ts < cutoff or not hb.get("alive", True):
                    dead.append(hb)
        return dead

    def iter_events(
        self, timeout: Optional[float] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield events as they arrive.

        Args:
            timeout: Total seconds to listen. None means indefinite.

        Yields:
            Event data dicts.
        """
        if not self._use_valkey or self._pubsub is None:
            logger.warning("iter_events: no Valkey connection")
            return

        deadline = time.time() + timeout if timeout is not None else None

        while True:
            if deadline is not None and time.time() >= deadline:
                return

            try:
                message = self._pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message.get("type") in ("message", "pmessage"):
                    raw = message.get("data", "")
                    if isinstance(raw, str):
                        try:
                            data = json.loads(raw)
                            self._handle_message(data)
                            yield data
                        except (json.JSONDecodeError, ValueError):
                            pass
            except Exception as e:
                logger.debug("iter_events error: %s", e)
                time.sleep(0.5)

    def stop(self) -> None:
        """Stop the listener thread and clean up."""
        self._listener_stop.set()
        if self._listener_thread is not None:
            self._listener_thread.join(timeout=2)
            self._listener_thread = None
        if self._pubsub is not None:
            try:
                self._pubsub.unsubscribe()
                self._pubsub.punsubscribe()
                self._pubsub.close()
            except Exception:
                pass
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
