"""Claude Code adapter (ADR-033 + ADR-033b).

Translates Claude Code hook payloads (PreToolUse:Agent, PostToolUse:Agent,
PostToolUse:* for generic tools) into canonical events.

Mirrors the legacy logic in ``hooks/native-agent-heartbeat.sh`` so behaviour is
preserved while capture is decoupled from the harness.

ADR-033b: ``duration_ms`` is now computed from Pre/Post correlation via
:class:`~lib.harness_adapter.tool_use_correlation.CorrelationStore` instead of
relying on a non-existent ``started_at`` field in the Post payload. On
``PreToolUse:Agent`` the adapter records the start time; on
``PostToolUse:Agent`` it pops it and computes the real elapsed milliseconds.
"""

from __future__ import annotations

import os
import time
from typing import Any, ClassVar, Dict, List, Optional

from .base import (
    AgentEnd,
    AgentStart,
    CanonicalEvent,
    HarnessAdapter,
    HarnessName,
    HeartbeatTick,
    TokenUsage,
    ToolUse,
    now_epoch,
)
from .tool_use_correlation import CorrelationStore


class ClaudeCodeAdapter(HarnessAdapter):
    """Adapter for Anthropic's Claude Code harness."""

    name: ClassVar[HarnessName] = HarnessName.CLAUDE_CODE

    #: Heartbeat stream expected by ``AgentBusMetrics.on_heartbeat_event``.
    default_output: ClassVar[str] = ".cognitive-os/metrics/agent-heartbeat.jsonl"

    def __init__(
        self,
        project_dir=None,
        correlation_store: Optional[CorrelationStore] = None,
    ) -> None:
        super().__init__(project_dir)
        # ADR-033b: shared correlation store; callers may inject a custom one
        # for testing or cross-process recovery.
        self._correlation: CorrelationStore = correlation_store or CorrelationStore(
            project_dir=self.project_dir
        )
        # ADR-038 Gap #4: per-agent PostToolUse:Agent event counter within
        # this adapter instance (i.e. within the current hook invocation
        # lifetime). Counts are also persisted across invocations via
        # _reasoning_cycle_file so the heartbeat payload carries a session-
        # cumulative count.
        self._cycle_counts: dict[str, int] = {}

    # --- detection ---------------------------------------------------------

    @classmethod
    def detect_harness(cls, raw: Any) -> Optional[HarnessName]:
        if not isinstance(raw, dict):
            return None
        # Strong signal: CC hooks carry "tool_name" + "tool_use_id" at top-level
        # (PreToolUse) or additionally "tool_response" (PostToolUse).
        if "tool_name" in raw and ("tool_use_id" in raw or "tool_input" in raw):
            return cls.name
        return None

    # --- parsing -----------------------------------------------------------

    def parse_event(self, raw: Dict[str, Any]) -> List[CanonicalEvent]:
        if not isinstance(raw, dict):
            return []

        tool_name = raw.get("tool_name", "")
        tool_use_id = (
            raw.get("tool_use_id")
            or raw.get("tool_input", {}).get("tool_use_id")
            or "native-agent-unknown"
        )
        is_post = "tool_response" in raw
        session_id = os.environ.get("COGNITIVE_OS_SESSION_ID", "") or None
        ts = now_epoch()
        cwd = raw.get("cwd") or os.environ.get(
            "COGNITIVE_OS_PROJECT_DIR",
            os.environ.get("CLAUDE_PROJECT_DIR"),
        )

        events: List[CanonicalEvent] = []

        if tool_name == "Agent":
            # Agent lifecycle → canonical AgentStart / AgentEnd plus a
            # heartbeat for backward-compat with agent-heartbeat.jsonl readers.
            if is_post:
                # ADR-033b: look up real start time from correlation store
                duration_ms = self._compute_duration_ms(tool_use_id)
                usage = _extract_token_usage(raw.get("tool_response"))
                # ADR-038 Gap #4: increment reasoning cycle count on every
                # PostToolUse:Agent (each post = one completed think→act→observe
                # cycle), then reset after the final tick is emitted.
                cycle_count = self._increment_cycle_count(tool_use_id)
                events.append(
                    AgentEnd(
                        agent_id=tool_use_id,
                        ended_at=ts,
                        exit_status=_exit_status(raw),
                        duration_ms=duration_ms,
                        token_usage=usage,
                        session_id=session_id,
                    )
                )
                events.append(
                    HeartbeatTick(
                        agent_id=tool_use_id,
                        ts=ts,
                        alive=False,
                        session_id=session_id,
                        reasoning_cycle_count=cycle_count,
                    )
                )
                self._reset_cycle_count(tool_use_id)
                if any(v for v in usage.values()):
                    events.append(
                        TokenUsage(
                            agent_id=tool_use_id,
                            ts=ts,
                            input_tokens=usage.get("input", 0),
                            output_tokens=usage.get("output", 0),
                            cache_read=usage.get("cached"),
                            session_id=session_id,
                        )
                    )
            else:
                # ADR-033b: record start time for correlation
                self._correlation.record(tool_use_id, time.monotonic())
                events.append(
                    AgentStart(
                        agent_id=tool_use_id,
                        started_at=ts,
                        tool_name=tool_name,
                        cwd=cwd,
                        input_summary=_summarize(raw.get("tool_input")),
                        session_id=session_id,
                    )
                )
                events.append(
                    HeartbeatTick(
                        agent_id=tool_use_id,
                        ts=ts,
                        alive=True,
                        session_id=session_id,
                        reasoning_cycle_count=0,
                    )
                )
        else:
            # Generic tool use — only post-events carry meaningful status.
            if is_post:
                events.append(
                    ToolUse(
                        agent_id=tool_use_id,
                        tool_name=tool_name,
                        started_at=ts,
                        exit_status=_exit_status(raw),
                        session_id=session_id,
                    )
                )

        return events

    # --- reasoning cycle tracking ------------------------------------------

    @property
    def _reasoning_cycle_file(self):
        return (
            self.project_dir
            / ".cognitive-os"
            / "metrics"
            / "reasoning-cycle-counts.jsonl"
        )

    def _load_cycle_count(self, agent_id: str) -> int:
        """Return the persisted cumulative reasoning cycle count for agent_id."""
        path = self._reasoning_cycle_file
        if not path.exists():
            return 0
        count = 0
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    import json as _json
                    rec = _json.loads(line)
                except Exception:
                    continue
                if rec.get("agent_id") == agent_id:
                    count = rec.get("cycle_count", count)
        except OSError:
            pass
        return count

    def _save_cycle_count(self, agent_id: str, count: int) -> None:
        """Append the updated cycle count to the persistent JSONL."""
        import json as _json
        path = self._reasoning_cycle_file
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "agent_id": agent_id,
            "cycle_count": count,
            "ts": time.time(),
        }
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(_json.dumps(record) + "\n")
        except OSError:
            pass

    def _increment_cycle_count(self, agent_id: str) -> int:
        """Increment and persist the reasoning cycle count; return new value."""
        current = self._cycle_counts.get(agent_id)
        if current is None:
            current = self._load_cycle_count(agent_id)
        current += 1
        self._cycle_counts[agent_id] = current
        self._save_cycle_count(agent_id, current)
        return current

    def _reset_cycle_count(self, agent_id: str) -> None:
        """Reset the cycle count on AgentEnd (after recording the final tick)."""
        self._cycle_counts.pop(agent_id, None)

    # --- duration ----------------------------------------------------------

    def _compute_duration_ms(self, tool_use_id: str) -> Optional[int]:
        """Pop the stored start time and return elapsed milliseconds.

        ADR-033b: replaces the aspirational ``_duration_ms(raw, ts)`` helper
        that read a ``started_at`` field that CC payloads never include.
        Returns ``None`` when no Pre event was seen for this ID (e.g. the
        process was restarted between Pre and Post).
        """
        started = self._correlation.pop(tool_use_id)
        if started is None:
            return None
        elapsed = time.monotonic() - started
        return max(0, int(elapsed * 1000))

    # --- compatibility emit -----------------------------------------------

    def emit_fallback_bus_legacy(self, event: HeartbeatTick) -> None:
        """Write the FallbackBus per-agent heartbeat.jsonl that predates ADR-033.

        Consumers (bus subscribers, fallback scanners) expect this file at
        ``.cognitive-os/agent-bus/<agent_id>/heartbeat.jsonl`` with the exact
        legacy payload shape. Preserved for schema compatibility.
        """
        try:
            import json
            agent_dir = (
                self.project_dir / ".cognitive-os" / "agent-bus" / event.agent_id
            )
            agent_dir.mkdir(parents=True, exist_ok=True)
            hb_file = agent_dir / "heartbeat.jsonl"
            payload = {
                "type": "heartbeat",
                "agent_id": event.agent_id,
                "session_id": event.session_id or "",
                "alive": event.alive,
                "timestamp_epoch": event.ts,
                "phase": "launched" if event.alive else "completed",
                "tokens_used": 0,
                "source": "native-agent-heartbeat-hook",
            }
            with open(hb_file, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload) + "\n")
        except Exception:
            pass

    def emit_heartbeat_legacy(self, event: HeartbeatTick) -> None:
        """Also notify AgentBusMetrics so legacy consumers see the tick.

        Safe to call repeatedly; failures are swallowed so capture never
        blocks a hook.
        """
        try:
            from lib.agent_bus_metrics import AgentBusMetrics  # type: ignore
        except Exception:
            return
        try:
            metrics = AgentBusMetrics(
                metrics_path=str(
                    self.project_dir / ".cognitive-os/metrics/agent-heartbeat.jsonl"
                )
            )
            metrics.on_heartbeat_event(
                {
                    "agent_id": event.agent_id,
                    "session_id": event.session_id or "",
                    "alive": event.alive,
                    "timestamp_epoch": event.ts,
                    "tokens_used": 0,
                }
            )
        except Exception:
            # Never let observability capture kill the hook
            pass


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _extract_token_usage(tool_response: Any) -> Dict[str, int]:
    if not isinstance(tool_response, dict):
        return {"input": 0, "output": 0, "cached": 0}
    usage = tool_response.get("usage") or {}
    if not isinstance(usage, dict):
        return {"input": 0, "output": 0, "cached": 0}
    return {
        "input": int(usage.get("input_tokens") or 0),
        "output": int(usage.get("output_tokens") or 0),
        "cached": int(
            usage.get("cache_read_input_tokens")
            or usage.get("cached_tokens")
            or 0
        ),
    }


def _exit_status(raw: Dict[str, Any]) -> str:
    resp = raw.get("tool_response")
    if isinstance(resp, dict):
        if resp.get("is_error"):
            return "error"
        if resp.get("error"):
            return "error"
        return "success"
    return "unknown"


def _summarize(tool_input: Any, limit: int = 160) -> Optional[str]:
    if not tool_input:
        return None
    if isinstance(tool_input, dict):
        prompt = tool_input.get("prompt") or tool_input.get("description")
        if prompt:
            return str(prompt)[:limit]
    return str(tool_input)[:limit]
