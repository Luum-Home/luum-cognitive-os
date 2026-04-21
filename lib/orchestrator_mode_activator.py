# SCOPE: both
"""Orchestrator mode activation logic.

Checks if Valkey is reachable and, when it is, activates executor mode
for the current process by setting ORCHESTRATOR_MODE in os.environ.

Renamed from lib/auto_executor.py (v0.15).  The old name is kept as a
deprecation shim — import lib.auto_executor to get a deprecation warning
and the same API.

Python 3.9+ compatible. No external dependencies required.
"""

import logging
import os
import socket
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

_VALKEY_HOST_DEFAULT = "localhost"
_VALKEY_PORT_DEFAULT = 6379
_CONNECT_TIMEOUT_S = 1.0


def _is_valkey_reachable(host: str = _VALKEY_HOST_DEFAULT, port: int = _VALKEY_PORT_DEFAULT) -> bool:
    """TCP connect check — returns True when Valkey is listening."""
    try:
        with socket.create_connection((host, port), timeout=_CONNECT_TIMEOUT_S):
            return True
    except (OSError, socket.timeout):
        return False


class AutoExecutor:
    """Auto-activates executor mode when infrastructure is available."""

    @staticmethod
    def check_and_activate() -> Dict:
        """Check if executor mode should be activated.

        Logic:
        1. Check if Valkey is reachable (TCP connect to localhost:6379).
        2. If yes AND ORCHESTRATOR_MODE not set: set it to 'executor'.
        3. If yes AND already set: confirm.
        4. If no: stay in fire-and-forget.

        Returns:
            {
              "mode": "connected" | "fire_and_forget",
              "valkey_available": bool,
              "auto_activated": bool,
              "message": str,
            }
        """
        try:
            host = os.environ.get("VALKEY_HOST", _VALKEY_HOST_DEFAULT)
            port = int(os.environ.get("VALKEY_PORT", str(_VALKEY_PORT_DEFAULT)))
            valkey_ok = _is_valkey_reachable(host, port)
        except Exception as exc:
            logger.debug("Valkey check failed: %s", exc)
            valkey_ok = False

        already_set = os.environ.get("ORCHESTRATOR_MODE", "").lower() == "executor"
        auto_activated = False

        if valkey_ok:
            if not already_set:
                os.environ["ORCHESTRATOR_MODE"] = "executor"
                auto_activated = True
                message = "Valkey reachable — executor mode auto-activated for this process."
            else:
                message = "Valkey reachable — executor mode already active."
            mode = "connected"
        else:
            message = "Valkey not reachable — using fire-and-forget mode (Agent tool)."
            mode = "fire_and_forget"

        return {
            "mode": mode,
            "valkey_available": valkey_ok,
            "auto_activated": auto_activated,
            "message": message,
        }

    @staticmethod
    def should_use_executor() -> bool:
        """Quick check: should we use executor mode?

        Returns True when ORCHESTRATOR_MODE=executor is set in the environment.
        """
        return os.environ.get("ORCHESTRATOR_MODE", "").lower() == "executor"

    @staticmethod
    def get_launch_function() -> Optional[Callable]:
        """Return the appropriate agent launch function based on mode.

        CONNECTED  → delegate_task from lib.orchestrator_mode
        FIRE_AND_FORGET → None (caller should use Agent tool)
        """
        if not AutoExecutor.should_use_executor():
            return None
        try:
            from lib.orchestrator_mode import delegate_task  # type: ignore[import]
            return delegate_task
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not import delegate_task: %s", exc)
            return None

    @staticmethod
    def format_launch_advice() -> str:
        """One-line advice for the orchestrator on how to launch agents."""
        if AutoExecutor.should_use_executor():
            return (
                "CONNECTED: Use delegate_task() from lib.orchestrator_mode "
                "for bidirectional comms (heartbeat, Q&A, graceful stop)."
            )
        return (
            "FIRE_AND_FORGET: Use Agent tool — include ALL context in the initial prompt. "
            "No mid-execution communication is possible."
        )
