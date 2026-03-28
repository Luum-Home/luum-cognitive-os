"""Orchestrator Mode -- subprocess-based delegation via ClaudeExecutor.

When ``ORCHESTRATOR_MODE=executor`` the orchestrator delegates work to
sub-agents through :class:`lib.claude_executor.ClaudeExecutor` (subprocess)
instead of the built-in Agent tool.  This gives:

* Valkey pub/sub communication (heartbeat, progress, Q&A)
* Full context isolation (each agent gets a fresh context)
* Real-time streaming of agent progress
* File lock coordination between agents

The default is ``off`` -- the normal Agent tool (fire-and-forget) is used.

Python 3.9+ compatible.
"""

import logging
import os
import uuid
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def is_executor_mode() -> bool:
    """Return ``True`` when ``ORCHESTRATOR_MODE=executor`` is set."""
    return os.environ.get("ORCHESTRATOR_MODE", "").lower() == "executor"


def _generate_agent_id(prefix: str = "agent") -> str:
    """Generate a short unique agent ID."""
    short = uuid.uuid4().hex[:8]
    return "%s-%s" % (prefix, short)


def _get_model_for_phase(phase: str) -> str:
    """Look up the recommended model for an SDD *phase* via the routing table.

    Falls back to ``"sonnet"`` when the router is unavailable or the phase
    is not in the table.
    """
    try:
        from lib.model_router import select_model

        return select_model(phase)
    except Exception:
        # Routing table not available -- use safe default
        _PHASE_DEFAULTS: Dict[str, str] = {
            "sdd-propose": "opus",
            "sdd-design": "opus",
            "systematic-debugging": "opus",
            "sdd-spec": "sonnet",
            "sdd-tasks": "sonnet",
            "sdd-apply": "sonnet",
            "sdd-verify": "sonnet",
            "sdd-archive": "haiku",
        }
        return _PHASE_DEFAULTS.get(phase, "sonnet")


def delegate_task(
    task: str,
    model: str = "sonnet",
    working_dir: Optional[str] = None,
    agent_id: Optional[str] = None,
    timeout: int = 600,
) -> Dict:
    """Delegate *task* via :class:`ClaudeExecutor` instead of the Agent tool.

    Args:
        task: The prompt / instructions for the sub-agent.
        model: Model short-name (``opus`` / ``sonnet`` / ``haiku``) or full ID.
        working_dir: Working directory for the subprocess. Defaults to cwd.
        agent_id: Optional agent identifier for bus communication.
                  Auto-generated when omitted.
        timeout: Timeout in seconds (default 600).

    Returns:
        A dict with keys ``success``, ``result``, ``cost_usd``,
        ``duration_secs``, ``tokens_in``, ``tokens_out``,
        ``model_used``, and ``agent_id``.
    """
    try:
        from lib.claude_executor import ClaudeExecutor
    except ImportError:
        logger.error("ClaudeExecutor not available -- cannot delegate task")
        return {
            "success": False,
            "result": "ClaudeExecutor is not available",
            "cost_usd": 0.0,
            "duration_secs": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "model_used": model,
            "agent_id": agent_id or "",
        }

    aid = agent_id or _generate_agent_id()
    executor = ClaudeExecutor(
        working_dir=working_dir or os.getcwd(),
        default_model=model,
        default_timeout=timeout,
        agent_id=aid,
    )

    result = executor.run(task, model=model, timeout=timeout)

    return {
        "success": result.success,
        "result": result.result_text,
        "cost_usd": result.cost_usd,
        "duration_secs": result.duration_secs,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "model_used": result.model_used or model,
        "agent_id": aid,
    }


def delegate_sdd_phase(
    change_name: str,
    phase: str,
    model: Optional[str] = None,
    working_dir: Optional[str] = None,
    timeout: int = 600,
) -> Dict:
    """Delegate an SDD phase via :class:`ClaudeExecutor`.

    Uses the model-routing table to select the appropriate model unless
    *model* is explicitly provided.

    Args:
        change_name: SDD change identifier (e.g. ``"auth-refactor"``).
        phase: SDD phase name (e.g. ``"sdd-apply"``).
        model: Override model; ``None`` uses the routing table.
        working_dir: Working directory for the subprocess.
        timeout: Timeout in seconds.

    Returns:
        Same dict shape as :func:`delegate_task`.
    """
    effective_model = model or _get_model_for_phase(phase)
    agent_id = _generate_agent_id(prefix=phase)
    task_prompt = "Run SDD phase '%s' for change '%s'." % (phase, change_name)

    return delegate_task(
        task=task_prompt,
        model=effective_model,
        working_dir=working_dir,
        agent_id=agent_id,
        timeout=timeout,
    )
