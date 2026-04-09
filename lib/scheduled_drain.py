"""Scheduled Drain — combined queue drain + health check helper.

Called by the CronCreate-based periodic queue drain task (Phase 4A of the
agent orchestration plan). Combines QueueDrainer and AgentHealthMonitor into
a single callable that returns an actionable report for the orchestrator.

Usage from CronCreate prompt:
    python3 -c "from lib.scheduled_drain import drain_and_report; print(drain_and_report())"

Python 3.9+ compatible. No external dependencies. Author: luum.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from lib.queue_drainer import QueueDrainer

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CRON_INTERVAL = "*/5 * * * *"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def drain_and_report(
    queue_path: str | None = None,
    tasks_path: str | None = None,
    max_parallel: int | None = None,
) -> str:
    """Combined queue drain + health check. Returns an actionable report.

    The report has two sections:

    1. Queue drain line — e.g. "QUEUE DRAIN: 2 agent(s) ready to launch …"
    2. Agent health section — from AgentHealthMonitor (if available)

    The orchestrator should:
    - If "N agent(s) ready to launch": call get_ready_agents() and launch them.
    - If queue is empty: cancel the scheduled drain task (saves tokens).
    - If health issues are reported: act on dead/stuck agents.

    Args:
        queue_path:   Override default queue file path (for testing).
        tasks_path:   Override default active-tasks file path (for testing).
        max_parallel: Override max_parallel_agents from config (for testing).

    Returns:
        Human-readable report string for the orchestrator.
    """
    kwargs: Dict[str, Any] = {}
    if queue_path is not None:
        kwargs["queue_path"] = queue_path
    if tasks_path is not None:
        kwargs["tasks_path"] = tasks_path
    if max_parallel is not None:
        kwargs["max_parallel"] = max_parallel

    drainer = QueueDrainer(**kwargs)
    drain_line = drainer.format_drain_instruction()

    # Try to import health monitor (Phase 3 — may not exist yet)
    health_section = _get_health_report(tasks_path=tasks_path)

    return f"{drain_line}\n\n{health_section}"


def should_schedule_drain(
    queue_path: str | None = None,
    tasks_path: str | None = None,
) -> bool:
    """Return True if the queue has items worth scheduling a drain for.

    The orchestrator should only create a CronCreate task when this returns
    True. When it returns False, the queue is empty and periodic polling would
    waste tokens.

    Args:
        queue_path: Override default queue file path (for testing).
        tasks_path: Override default active-tasks file path (for testing).

    Returns:
        True if there are queued items or dispatching items pending.
    """
    kwargs: Dict[str, Any] = {}
    if queue_path is not None:
        kwargs["queue_path"] = queue_path
    if tasks_path is not None:
        kwargs["tasks_path"] = tasks_path

    drainer = QueueDrainer(**kwargs)
    queued = drainer.queue_length(status="queued")
    dispatching = drainer.queue_length(status="dispatching")
    return (queued + dispatching) > 0


def get_cron_create_spec() -> Dict[str, Any]:
    """Return the CronCreate specification for periodic queue drain polling.

    The returned dict can be passed to the CronCreate tool (or equivalent)
    to set up a recurring drain task. The task should be cancelled (or not
    recreated) when should_schedule_drain() returns False.

    Returns:
        Dict with keys: cron, prompt, recurring, description.
    """
    return {
        "cron": _DEFAULT_CRON_INTERVAL,
        "prompt": (
            "Check the agent dispatch queue and launch any ready agents.\n\n"
            "1. Run: python3 -c \"from lib.scheduled_drain import drain_and_report; "
            "print(drain_and_report())\"\n"
            "2. If agents are ready (output shows 'N agent(s) ready to launch'), "
            "launch them using the Agent tool with the queued prompt and model.\n"
            "3. For each launched agent: call "
            "QueueDrainer().mark_dispatched(agent_id) before launch and "
            "QueueDrainer().remove_completed(agent_id) after.\n"
            "4. If dead or stuck agents are reported, escalate to the user.\n"
            "5. If the queue is empty (output shows 'dispatch queue is empty'), "
            "report 'Queue empty — no action needed' and do NOT reschedule "
            "this drain task."
        ),
        "recurring": True,
        "description": "Periodic agent queue drain and health check (every 5 minutes)",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_health_report(tasks_path: str | None = None) -> str:
    """Return health report from AgentHealthMonitor, or a fallback message."""
    try:
        from lib.agent_health_monitor import AgentHealthMonitor  # type: ignore[import]

        kwargs: Dict[str, Any] = {}
        if tasks_path is not None:
            kwargs["tasks_path"] = tasks_path
        monitor = AgentHealthMonitor(**kwargs)
        return monitor.format_health_report()
    except ImportError:
        return "AGENT HEALTH: monitor not available (lib/agent_health_monitor.py not found)"
    except Exception as exc:  # noqa: BLE001
        return f"AGENT HEALTH: error running health check — {exc}"
