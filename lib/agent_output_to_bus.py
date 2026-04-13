# scope: both
"""Agent Output Bridge — publishes file-based agent progress to Valkey AgentBus.

Bridges the gap between Claude Code's Agent tool (which writes JSONL output files)
and the Valkey pub/sub AgentBus used for real-time orchestrator monitoring.

Usage:
    bridge = AgentOutputBridge(output_dir=".cognitive-os/agent-outputs")
    bridge.sync_once()      # publish all current statuses to Valkey
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from lib.agent_bus import AgentPublisher
from lib.agent_output_monitor import AgentOutputMonitor, AgentStatus

logger = logging.getLogger(__name__)


class AgentOutputBridge:
    """Bridges Agent tool JSONL output files to the Valkey AgentBus.

    Reads output files via AgentOutputMonitor, then publishes each agent's
    latest status as a progress event on the Valkey AgentBus.

    Args:
        output_dir: Directory where agent output files are written.
        valkey_url: Redis-compatible Valkey connection URL.
        fallback_dir: File-based fallback directory for AgentPublisher.
    """

    def __init__(
        self,
        output_dir: str,
        valkey_url: str = "redis://localhost:6379",
        fallback_dir: Optional[str] = None,
    ) -> None:
        self.output_dir = output_dir
        self.valkey_url = valkey_url
        self.fallback_dir = fallback_dir
        self._monitor = AgentOutputMonitor(output_dir)
        # Cache of publishers keyed by agent_id to avoid reconnecting every sync
        self._publishers: dict[str, AgentPublisher] = {}

    def _get_publisher(self, agent_id: str) -> AgentPublisher:
        """Return (or create) an AgentPublisher for the given agent_id."""
        if agent_id not in self._publishers:
            self._publishers[agent_id] = AgentPublisher(
                agent_id=agent_id,
                valkey_url=self.valkey_url,
                fallback_dir=self.fallback_dir,
            )
        return self._publishers[agent_id]

    def sync_once(self) -> list[AgentStatus]:
        """Read all output files and publish the latest status to Valkey.

        Returns:
            List of AgentStatus objects that were synced.
        """
        statuses = self._monitor.check_all()

        for status in statuses:
            try:
                self.publish_status(status)
            except Exception as exc:
                logger.warning(
                    "Failed to publish status for agent %s: %s", status.agent_id, exc
                )

        return statuses

    def publish_status(self, status: AgentStatus) -> None:
        """Publish one agent's status to the AgentBus.

        Uses ``AgentPublisher.progress()`` for in-progress agents and
        ``AgentPublisher.report_complete()`` for completed agents.

        Args:
            status: AgentStatus snapshot to publish.
        """
        publisher = self._get_publisher(status.agent_id)

        if status.status == "completed":
            summary = status.last_assistant_text or "Agent completed (no text captured)"
            publisher.report_complete(summary)
            logger.debug("Published completion for agent %s", status.agent_id)
            return

        # Build a human-readable action string
        if status.last_progress_marker:
            action = status.last_progress_marker[:200]
        elif status.last_assistant_text:
            action = status.last_assistant_text[:200]
        else:
            action = "running (%s)" % status.status

        step_current = status.progress_step or 0
        step_total = status.progress_total or 0

        publisher.progress(
            tool="Agent",
            file=self.output_dir,
            action=action,
            step_current=step_current,
            step_total=step_total,
        )
        logger.debug(
            "Published progress for agent %s: %s (step %d/%d)",
            status.agent_id,
            action[:60],
            step_current,
            step_total,
        )

    def close(self) -> None:
        """Stop all publisher heartbeat threads."""
        for publisher in self._publishers.values():
            try:
                publisher.stop()
            except Exception as exc:
                logger.debug("Error stopping publisher: %s", exc)
        self._publishers.clear()
