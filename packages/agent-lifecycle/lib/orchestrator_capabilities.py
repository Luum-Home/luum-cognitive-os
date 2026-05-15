# SCOPE: both
"""Orchestrator capability detector — auto-detects available communication modes.

At session start, call ``OrchestratorCapabilities().detect()`` once to learn
what the current environment supports, then use the properties to guide how
agents are launched and monitored.

Python 3.9+ compatible. No external dependencies required.
"""

import logging
import os
import socket
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


class OrchestratorCapabilities:
    """Auto-detects what communication capabilities are available.

    Usage::

        caps = OrchestratorCapabilities().detect()
        print(caps.format_status())
        print(caps.get_agent_launch_advice())
    """

    class CommMode:
        FIRE_AND_FORGET = "fire_and_forget"  # Agent tool only, no mid-exec comms
        CONNECTED = "connected"  # Executor + Valkey, full bidirectional

    def __init__(self) -> None:
        self._mode: Optional[str] = None
        self._valkey_available: Optional[bool] = None
        self._executor_available: Optional[bool] = None
        self._docker_running: Optional[bool] = None
        self._valkey_container_exists: Optional[bool] = None

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self) -> "OrchestratorCapabilities":
        """Run all detection checks. Safe to call multiple times (idempotent)."""
        if self._mode is not None:
            return self  # already detected

        self._executor_available = self._check_executor()
        self._valkey_available = self._check_valkey()
        self._docker_running = self._check_docker()
        if self._docker_running:
            self._valkey_container_exists = self._check_valkey_container()
        else:
            self._valkey_container_exists = False

        if self._executor_available and self._valkey_available:
            self._mode = self.CommMode.CONNECTED
        else:
            self._mode = self.CommMode.FIRE_AND_FORGET

        return self

    def _check_executor(self) -> bool:
        if os.environ.get("ORCHESTRATOR_MODE", "").lower() == "executor":
            return True
        # ADR-034: the cos-executor daemon writes .cognitive-os/runtime/
        # orchestrator-mode with the value "executor" while it is running.
        # Reading this lets the banner reflect reality even when the env
        # var was not exported into this process.
        try:
            from pathlib import Path
            project = Path(
                os.environ.get("COGNITIVE_OS_PROJECT_DIR",
                               os.environ.get("CLAUDE_PROJECT_DIR",
                                              os.getcwd()))
            )
            state = project / ".cognitive-os" / "runtime" / "orchestrator-mode"
            pid_file = project / ".cognitive-os" / "runtime" / "cos-executor.pid"
            if state.exists() and state.read_text().strip().lower() == "executor":
                # Verify the daemon PID is still alive; a stale mode file
                # without a live PID should not flip the banner to ✅.
                if pid_file.exists():
                    try:
                        pid = int(pid_file.read_text().strip() or "0")
                        if pid > 0:
                            os.kill(pid, 0)
                            return True
                    except (OSError, ValueError):
                        return False
        except Exception:
            pass
        return False

    def _check_valkey(self) -> bool:
        host = os.environ.get("VALKEY_HOST", "localhost")
        port = int(os.environ.get("VALKEY_PORT", "6379"))
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except (OSError, socket.timeout):
            return False

    def _check_docker(self) -> bool:
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                timeout=2,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    def _check_valkey_container(self) -> bool:
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=valkey", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return bool(result.stdout.strip())
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    def _require_detected(self) -> None:
        if self._mode is None:
            raise RuntimeError("Call detect() before accessing capabilities.")

    @property
    def mode(self) -> str:
        self._require_detected()
        return self._mode  # type: ignore[return-value]

    @property
    def can_send_to_agent(self) -> bool:
        self._require_detected()
        return self._mode == self.CommMode.CONNECTED

    @property
    def can_receive_heartbeat(self) -> bool:
        self._require_detected()
        return self._mode == self.CommMode.CONNECTED

    @property
    def can_ask_questions(self) -> bool:
        self._require_detected()
        return self._mode == self.CommMode.CONNECTED

    @property
    def can_stop_gracefully(self) -> bool:
        self._require_detected()
        return self._mode == self.CommMode.CONNECTED

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_status(self) -> str:
        """One-line status for session start."""
        self._require_detected()
        v = "✅" if self._valkey_available else "❌"
        e = "✅" if self._executor_available else "❌"
        mode = str(self._mode or "unknown")
        return f"Agent comms: {mode.upper()} (Valkey {v}, Executor {e})"

    def format_capabilities(self) -> str:
        """Multi-line capability report."""
        self._require_detected()
        yes, no = "✅", "❌"
        lines = [
            "Agent Communication:",
            f"  Mode: {str(self._mode or 'unknown').upper()}",
            f"  Send to agent:  {yes if self.can_send_to_agent else no} (via Valkey pub/sub)" if self.can_send_to_agent else f"  Send to agent:  {no}",
            f"  Heartbeat:      {yes if self.can_receive_heartbeat else no}" + (" (5s interval)" if self.can_receive_heartbeat else ""),
            f"  Q&A mid-exec:   {yes if self.can_ask_questions else no}",
            f"  Graceful stop:  {yes if self.can_stop_gracefully else no}",
        ]
        if not self._valkey_available and self._docker_running and self._valkey_container_exists:
            lines.append("  💡 Valkey container exists but is stopped — run: docker start valkey")
        return "\n".join(lines)

    def get_agent_launch_advice(self) -> str:
        """Advice for the orchestrator on how to launch agents."""
        self._require_detected()
        if self._mode == self.CommMode.FIRE_AND_FORGET:
            return (
                "Agents are fire-and-forget. Include ALL context in the initial prompt. "
                "No mid-execution communication is possible. "
                "Use TaskStop for kill only."
            )
        return (
            "Agents support bidirectional communication. You can:\n"
            "  - Monitor progress via heartbeat (5s interval)\n"
            "  - Answer clarification questions mid-execution\n"
            "  - Send stop/pause commands\n"
            "Use delegate_task() from lib/orchestrator_mode.py instead of the Agent tool."
        )

    def to_dict(self) -> dict:
        """Serialize for heartbeat/engram."""
        self._require_detected()
        return {
            "mode": self._mode,
            "valkey_available": self._valkey_available,
            "executor_available": self._executor_available,
            "docker_running": self._docker_running,
            "valkey_container_exists": self._valkey_container_exists,
            "capabilities": {
                "send_to_agent": self.can_send_to_agent,
                "heartbeat": self.can_receive_heartbeat,
                "ask_questions": self.can_ask_questions,
                "graceful_stop": self.can_stop_gracefully,
            },
        }
