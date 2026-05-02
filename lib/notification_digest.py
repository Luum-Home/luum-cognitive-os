# SCOPE: both
"""Notification digest — batches task-completion notifications into a compact summary."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class _Entry:
    task_id: str
    description: str
    status: str          # "completed" | "failed" | other
    result_summary: str
    duration_ms: int
    tool_uses: int
    tests: dict = field(default_factory=dict)  # {passed, failed, xfail}


class NotificationDigest:
    """Accumulates task notifications and presents them as a single digest."""

    def __init__(self) -> None:
        self._notifications: list[_Entry] = []

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(
        self,
        task_id: str,
        description: str,
        status: str,
        result_summary: str = "",
        duration_ms: int = 0,
        tool_uses: int = 0,
        tests: Optional[dict] = None,
    ) -> None:
        self._notifications.append(
            _Entry(task_id, description, status, result_summary,
                   duration_ms, tool_uses, tests or {})
        )

    def clear(self) -> None:
        self._notifications.clear()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def count(self) -> int:
        return len(self._notifications)

    def has_failures(self) -> bool:
        return any(n.status == "failed" for n in self._notifications)

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _trunc(text: str, limit: int = 80) -> str:
        return text if len(text) <= limit else text[:limit - 3] + "..."

    @staticmethod
    def _secs(ms: int) -> str:
        return f"{ms / 1000:.1f}s"

    def format_single(self, index: int = -1) -> str:
        if not self._notifications:
            return "(no notifications)"
        n = self._notifications[index]
        icon = "✅" if n.status != "failed" else "❌"
        summary = self._trunc(n.result_summary) if n.result_summary else n.status
        return (f"{icon} {self._trunc(n.description, 60)} — {summary} "
                f"({self._secs(n.duration_ms)}, {n.tool_uses} calls)")

    def format_digest(self, max_entries: int = 20, max_chars: int = 4000) -> str:
        """Return a bounded digest for orchestrator context."""
        if not self._notifications:
            return "=== AGENT DIGEST (0 completed) ===\n(nothing to report)\n================================"

        visible = self._notifications[-max_entries:] if max_entries > 0 else []
        omitted = max(0, self.count() - len(visible))
        lines: list[str] = [f"=== AGENT DIGEST ({self.count()} completed) ==="]
        if omitted:
            lines.append(f"… {omitted} older notifications omitted from detail rows")

        total_dur = 0
        total_tools = 0
        total_passed = total_failed = total_xfail = 0
        for n in self._notifications:
            total_dur += n.duration_ms
            total_tools += n.tool_uses
            total_passed += n.tests.get("passed", 0)
            total_failed += n.tests.get("failed", 0)
            total_xfail += n.tests.get("xfail", 0)

        for n in visible:
            icon = "✅" if n.status != "failed" else "❌"
            summary = self._trunc(n.result_summary) if n.result_summary else n.status
            lines.append(
                f"{icon} {self._trunc(n.description, 60)} — {summary} "
                f"({self._secs(n.duration_ms)}, {n.tool_uses} calls)"
            )

        if total_passed or total_failed or total_xfail:
            lines.append(
                f"Tests: {total_passed} passed, {total_failed} failed, {total_xfail} xfail"
            )
        lines.append(
            f"Total duration: {self._secs(total_dur)} | Total tool calls: {total_tools}"
        )
        lines.append("================================")
        result = "\n".join(lines)
        if max_chars > 0 and len(result) > max_chars:
            footer = "\n... [digest truncated]\n================================"
            return result[: max(0, max_chars - len(footer))] + footer
        return result

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> list[dict]:
        return [asdict(n) for n in self._notifications]

    @classmethod
    def from_dict(cls, data: list[dict]) -> "NotificationDigest":
        obj = cls()
        for item in data:
            obj._notifications.append(_Entry(**item))
        return obj
