"""Aider adapter — POC (ADR-033).

Aider does not invoke hooks. Instead, it writes a running transcript to
``.aider.chat.history.md`` at the project root. This adapter is a *passive
file-watcher* POC: given a raw payload ``{"history_file": "/path/.aider.chat.history.md"}``
or a tail delta in ``{"new_lines": ["..."]}``, it emits canonical events.

The goal of this adapter is to prove that the :class:`HarnessAdapter` API
generalizes beyond Claude Code's synchronous hook model. It is NOT a full
production capture path; a daemon watching the chat history for modifications
(inotify / fsevents) is the natural follow-up.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from .base import (
    AgentEnd,
    AgentStart,
    CanonicalEvent,
    HarnessAdapter,
    HarnessName,
    ToolUse,
    now_epoch,
)


# Aider chat history uses markdown ">" user blocks and "####" tool blocks.
_USER_RE = re.compile(r"^#### (.+)$")
_EDIT_RE = re.compile(r"^```(?P<lang>\w*)$")
_TOOL_RE = re.compile(r"^> (?P<tool>Ran shell command|Applied edit|Saved file): (?P<rest>.+)$")


class AiderAdapter(HarnessAdapter):
    """Passive file-watcher adapter for Aider."""

    name: ClassVar[HarnessName] = HarnessName.AIDER
    default_output: ClassVar[str] = ".cognitive-os/metrics/canonical-events.jsonl"

    # --- detection ---------------------------------------------------------

    @classmethod
    def detect_harness(cls, raw: Any) -> Optional[HarnessName]:
        if isinstance(raw, dict):
            hf = raw.get("history_file")
            if isinstance(hf, str) and hf.endswith(".aider.chat.history.md"):
                return cls.name
            if raw.get("harness") == cls.name.value:
                return cls.name
        if isinstance(raw, (str, Path)):
            p = str(raw)
            if p.endswith(".aider.chat.history.md"):
                return cls.name
        return None

    # --- parsing -----------------------------------------------------------

    def parse_event(self, raw: Dict[str, Any]) -> List[CanonicalEvent]:
        if not isinstance(raw, dict):
            return []

        lines = self._collect_lines(raw)
        if not lines:
            return []

        agent_id = raw.get("agent_id") or _stable_id(lines)
        session_id = raw.get("session_id")
        events: List[CanonicalEvent] = []

        # Mark start on first user prompt
        started = False
        for line in lines:
            stripped = line.rstrip("\n")
            if not started:
                m = _USER_RE.match(stripped)
                if m:
                    events.append(
                        AgentStart(
                            agent_id=agent_id,
                            started_at=now_epoch(),
                            tool_name="aider",
                            input_summary=m.group(1)[:160],
                            session_id=session_id,
                        )
                    )
                    started = True
                    continue
            m2 = _TOOL_RE.match(stripped)
            if m2:
                events.append(
                    ToolUse(
                        agent_id=agent_id,
                        tool_name=m2.group("tool"),
                        started_at=now_epoch(),
                        exit_status="success",
                        tool_input_hash=_hash(m2.group("rest")),
                        session_id=session_id,
                    )
                )

        # If the payload says this is a terminal delta, emit AgentEnd.
        if raw.get("final") or raw.get("ended"):
            events.append(
                AgentEnd(
                    agent_id=agent_id,
                    ended_at=now_epoch(),
                    exit_status=raw.get("exit_status", "success"),
                    token_usage=raw.get("token_usage") or {},
                    session_id=session_id,
                )
            )

        return events

    # --- helpers -----------------------------------------------------------

    def _collect_lines(self, raw: Dict[str, Any]) -> List[str]:
        if "new_lines" in raw:
            lines = raw["new_lines"]
            if isinstance(lines, list):
                return [str(x) for x in lines]
        if "history_file" in raw:
            try:
                return Path(raw["history_file"]).read_text(encoding="utf-8").splitlines()
            except OSError:
                return []
        return []


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _stable_id(lines: List[str]) -> str:
    sig = hashlib.sha1("\n".join(lines[:4]).encode("utf-8")).hexdigest()[:12]
    return f"aider-{sig}"


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
