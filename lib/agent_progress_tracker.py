# scope: both
"""
AgentProgressTracker — incremental Engram saves for sub-agents.

Sub-agents use this to save progress every 10 tool calls so partial work
survives TaskStop, suspension, or timeout.
"""

from __future__ import annotations

import re


class AgentProgressTracker:
    """Lightweight helper for incremental sub-agent progress saves."""

    SAVE_INTERVAL = 10

    def __init__(self, task_description: str, project: str = "luum-cognitive-os") -> None:
        self.task_description = task_description
        self.project = project
        self._topic_key = self.generate_topic_key()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def should_save(self, tool_call_number: int) -> bool:
        """Return True every 10th tool call (not at 0)."""
        return tool_call_number > 0 and tool_call_number % self.SAVE_INTERVAL == 0

    def generate_topic_key(self) -> str:
        """Stable topic key from first 5 words of the task description.

        'Fix auth bug in lib/auth.py' → 'agent-progress/fix-auth-bug-in-lib'
        """
        words = re.sub(r"[^a-zA-Z0-9\s]", "", self.task_description).split()
        slug = "-".join(w.lower() for w in words[:5]) or "unknown"
        return f"agent-progress/{slug}"

    def format_progress_save(
        self,
        tool_call_number: int,
        files_created: list[str] | None = None,
        files_modified: list[str] | None = None,
        findings: list[str] | None = None,
        status: str = "in_progress",
    ) -> dict:
        """Return a dict ready to pass to mem_save."""
        step = tool_call_number // self.SAVE_INTERVAL
        content = self._build_content(tool_call_number, step, status, files_created, files_modified, findings)
        return {
            "title": f"Progress: {self.task_description[:60]} — step {step}",
            "content": content,
            "type": "discovery",
            "topic_key": self._topic_key,
            "project": self.project,
        }

    def format_final_save(
        self,
        files_created: list[str] | None = None,
        files_modified: list[str] | None = None,
        findings: list[str] | None = None,
        result_summary: str = "",
    ) -> dict:
        """Return a dict for the final mem_save (status=completed).

        Uses the same topic_key so mem_save upserts (no duplicates).
        """
        content = self._build_content(None, None, "completed", files_created, files_modified, findings)
        if result_summary:
            content += f"\n**Result**: {result_summary}"
        return {
            "title": f"Completed: {self.task_description[:60]}",
            "content": content,
            "type": "discovery",
            "topic_key": self._topic_key,
            "project": self.project,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_content(
        self,
        tool_call_number: int | None,
        step: int | None,
        status: str,
        files_created: list[str] | None,
        files_modified: list[str] | None,
        findings: list[str] | None,
    ) -> str:
        lines = [f"**Task**: {self.task_description}"]
        if tool_call_number is not None and step is not None:
            lines.append(f"**Progress**: Step {step} ({tool_call_number} tool calls)")
        lines.append(f"**Status**: {status}")
        lines.append(f"**Files created**: {', '.join(files_created) if files_created else 'none'}")
        lines.append(f"**Files modified**: {', '.join(files_modified) if files_modified else 'none'}")
        lines.append(f"**Key findings**: {'; '.join(findings) if findings else 'none'}")
        return "\n".join(lines)
