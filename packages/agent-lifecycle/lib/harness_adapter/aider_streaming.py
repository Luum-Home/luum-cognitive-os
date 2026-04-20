"""Aider streaming adapter — ADR-034 POC.

Extends :class:`AiderAdapter` with a real-time ``stream_events`` generator
that tails ``.aider.chat.history.md`` and yields ADR-034 live canonical
events (:class:`ToolUseStart`, :class:`ToolUseEnd`, :class:`ProgressMarker`)
as the file grows.

This is intentionally a *polling* tail (0.5 s default) rather than inotify
so it runs unchanged on macOS, Linux and CI. The adapter maintains a byte
offset between calls so repeated invocations are cheap.

Usage from a daemon loop::

    adapter = AiderStreamingAdapter(project_dir)
    for event in adapter.stream_events(Path(".aider.chat.history.md"),
                                       poll_interval=0.5,
                                       stop_event=stop):
        bus.publish(event)
"""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import ClassVar, Generator, List, Optional

from .aider import AiderAdapter, _stable_id
from .base import (
    CanonicalEvent,
    HarnessName,
    ProgressMarker,
    ToolUseEnd,
    ToolUseStart,
    now_epoch,
)


# Reuse structure from aider.py but look for live markers.
_USER_RE = re.compile(r"^#### (.+)$")
_TOOL_START_RE = re.compile(
    r"^> (?P<tool>Running|Applying|Saving) (?P<rest>.+)$"
)
_TOOL_END_RE = re.compile(
    r"^> (?P<tool>Ran shell command|Applied edit|Saved file): (?P<rest>.+)$"
)
_PROGRESS_RE = re.compile(
    r"PROGRESS:\s*\[(?P<cur>\d+)\s*/\s*(?P<tot>\d+)\]\s*(?P<msg>.*)$"
)


class AiderStreamingAdapter(AiderAdapter):
    """Live, streaming variant of :class:`AiderAdapter`."""

    name: ClassVar[HarnessName] = HarnessName.AIDER

    def __init__(self, project_dir: Optional[Path] = None) -> None:
        super().__init__(project_dir)
        self._offsets: dict = {}
        self._agent_ids: dict = {}

    # ---- public API --------------------------------------------------

    def stream_events(
        self,
        history_file: Path,
        poll_interval: float = 0.5,
        stop_event: Optional[threading.Event] = None,
        max_iterations: Optional[int] = None,
    ) -> Generator[CanonicalEvent, None, None]:
        """Yield canonical live events as ``history_file`` grows.

        If ``stop_event`` is set, the generator exits cleanly.
        If ``max_iterations`` is supplied, the loop exits after that many
        polls (useful for tests).
        """
        path = Path(history_file)
        iters = 0
        while True:
            if max_iterations is not None and iters >= max_iterations:
                return

            new_lines = self._read_new_lines(path)
            for event in self.parse_live_lines(new_lines, path):
                yield event

            iters += 1
            # Check stop AFTER at least one pass so `stop.set()` pre-call
            # still produces one complete iteration (useful for tests).
            if stop_event is not None and stop_event.is_set():
                return
            time.sleep(poll_interval)

    def parse_live_lines(
        self, lines: List[str], source: Optional[Path] = None
    ) -> List[CanonicalEvent]:
        """Translate a batch of already-tailed lines into live events.

        Exposed for tests — avoids the polling loop so we can unit-test
        the parse logic in isolation.
        """
        if not lines:
            return []

        # Derive a stable agent id from the first few lines of the file
        # (same algorithm as AiderAdapter for continuity).
        key = str(source) if source else "<anonymous>"
        agent_id = self._agent_ids.setdefault(key, _stable_id(lines))
        out: List[CanonicalEvent] = []

        for line in lines:
            stripped = line.rstrip("\n")

            m_prog = _PROGRESS_RE.search(stripped)
            if m_prog:
                out.append(
                    ProgressMarker(
                        agent_id=agent_id,
                        ts=now_epoch(),
                        step_current=int(m_prog.group("cur")),
                        step_total=int(m_prog.group("tot")),
                        message=m_prog.group("msg").strip(),
                    )
                )
                continue

            m_start = _TOOL_START_RE.match(stripped)
            if m_start:
                out.append(
                    ToolUseStart(
                        agent_id=agent_id,
                        tool_name=m_start.group("tool"),
                        started_at=now_epoch(),
                        tool_input_summary=m_start.group("rest")[:160],
                    )
                )
                continue

            m_end = _TOOL_END_RE.match(stripped)
            if m_end:
                out.append(
                    ToolUseEnd(
                        agent_id=agent_id,
                        tool_name=m_end.group("tool"),
                        ended_at=now_epoch(),
                        duration_ms=0,
                        exit_status="success",
                    )
                )
                continue

            # User message line — treat as a cue that a new turn began, but
            # avoid duplicating AgentStart (already handled by the post-hoc
            # adapter on the full file).
            _ = _USER_RE.match(stripped)

        return out

    # ---- helpers -----------------------------------------------------

    def _read_new_lines(self, path: Path) -> List[str]:
        """Return lines appended since the last poll.

        Tracks a byte offset per path so repeated reads skip the prefix.
        If the file shrinks (rotation), offset is reset.
        """
        if not path.exists():
            return []

        try:
            size = path.stat().st_size
        except OSError:
            return []

        key = str(path)
        prev = self._offsets.get(key, 0)

        if size < prev:
            # File truncated / rotated; start fresh.
            prev = 0

        if size == prev:
            return []

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                fh.seek(prev)
                data = fh.read()
                self._offsets[key] = fh.tell()
        except OSError:
            return []

        if not data:
            return []
        return data.splitlines()
