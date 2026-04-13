"""Agent Output Monitor — read agent JSONL output files and extract progress.

Lightweight module for monitoring agents launched via Claude Code's Agent tool.
Reads output files without loading entire files into memory (tail-like approach).

JSONL format:
  - type == "assistant"  → assistant message with content blocks
  - type == "user"       → user prompt or tool_result blocks
  - type == "system"     → system events

Progress markers are embedded in assistant text as:
  PROGRESS: [step N/M] description
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# How many bytes to read from the end of a file for the "tail" approach
_TAIL_BYTES = 16 * 1024  # 16KB — enough for ~20 JSONL lines

# Regex for PROGRESS markers: "PROGRESS: [step 3/5] writing tests"
_PROGRESS_RE = re.compile(
    r"PROGRESS:\s*\[step\s+(\d+)/(\d+)\]([^\n]*)", re.IGNORECASE
)

# Seconds of inactivity before we consider an agent "idle"
_IDLE_THRESHOLD_S = 30

# Seconds of inactivity before we consider an agent "completed" (file not growing)
_COMPLETED_THRESHOLD_S = 300


@dataclass
class AgentStatus:
    """Status snapshot for a single running agent."""

    agent_id: str
    tool_call_count: int
    last_activity_ts: float
    last_progress_marker: Optional[str]  # e.g. "PROGRESS: [step 3/5] writing tests"
    last_assistant_text: Optional[str]   # last ~100 chars of assistant output
    file_size_bytes: int
    status: str  # "running" | "idle" | "completed" | "unknown"

    # Parsed progress fields (populated from last_progress_marker)
    progress_step: Optional[int] = field(default=None, repr=False)
    progress_total: Optional[int] = field(default=None, repr=False)

    @property
    def seconds_since_activity(self) -> float:
        return time.time() - self.last_activity_ts if self.last_activity_ts > 0 else float("inf")


def _read_tail(filepath: str, tail_bytes: int = _TAIL_BYTES) -> list[str]:
    """Read the last ``tail_bytes`` of a file and return complete JSONL lines.

    Uses seek to avoid loading the entire file.
    Returns lines in file order (oldest to newest within the tail window).
    """
    try:
        size = os.path.getsize(filepath)
    except OSError:
        return []

    if size == 0:
        return []

    read_offset = max(0, size - tail_bytes)

    try:
        with open(filepath, "rb") as fh:
            fh.seek(read_offset)
            raw = fh.read()
    except OSError:
        return []

    text = raw.decode("utf-8", errors="replace")

    # If we didn't start from the beginning, the first line may be partial
    lines = text.split("\n")
    if read_offset > 0 and lines:
        lines = lines[1:]  # discard potentially partial first line

    return [ln for ln in lines if ln.strip()]


def _parse_lines(lines: list[str]) -> tuple[int, Optional[str], Optional[str]]:
    """Parse JSONL lines and extract tool_call_count, last progress marker, last assistant text.

    Returns:
        (tool_call_count, last_progress_marker, last_assistant_text_snippet)
    """
    tool_call_count = 0
    last_progress_marker: Optional[str] = None
    last_assistant_text: Optional[str] = None

    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue

        if obj.get("type") != "assistant":
            continue

        content = obj.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue

        text_parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "tool_use":
                tool_call_count += 1
            elif btype == "text":
                text = block.get("text", "")
                if text:
                    text_parts.append(text)
                    # Check for PROGRESS marker
                    match = _PROGRESS_RE.search(text)
                    if match:
                        last_progress_marker = match.group(0).strip()

        if text_parts:
            combined = " ".join(text_parts)
            last_assistant_text = combined[-100:] if len(combined) > 100 else combined

    return tool_call_count, last_progress_marker, last_assistant_text


def _derive_status(
    file_size: int,
    last_activity_ts: float,
    tool_call_count: int,
) -> str:
    """Derive a status string from file metadata and activity timestamp."""
    if file_size == 0:
        return "unknown"

    age = time.time() - last_activity_ts
    if age < _IDLE_THRESHOLD_S:
        return "running"
    if age < _COMPLETED_THRESHOLD_S:
        return "idle"
    return "completed"


def _parse_progress_fields(
    marker: Optional[str],
) -> tuple[Optional[int], Optional[int]]:
    """Extract (step_current, step_total) from a PROGRESS marker string."""
    if not marker:
        return None, None
    match = _PROGRESS_RE.search(marker)
    if match:
        try:
            return int(match.group(1)), int(match.group(2))
        except (ValueError, IndexError):
            pass
    return None, None


class AgentOutputMonitor:
    """Monitor agent JSONL output files and report progress.

    Args:
        output_dir: Directory where agent output ``.jsonl`` files are written.
    """

    def __init__(self, output_dir: str) -> None:
        self.output_dir = output_dir

    def _output_files(self) -> list[str]:
        """Return paths of all ``.jsonl`` files in the output directory."""
        try:
            entries = os.listdir(self.output_dir)
        except OSError:
            return []
        return [
            os.path.join(self.output_dir, e)
            for e in entries
            if e.endswith(".jsonl") or e.endswith(".output")
        ]

    def _agent_id_from_path(self, filepath: str) -> str:
        """Derive agent_id from file path (basename without extension)."""
        name = os.path.basename(filepath)
        for ext in (".jsonl", ".output"):
            if name.endswith(ext):
                name = name[: -len(ext)]
                break
        return name

    def check_agent(self, agent_id: str) -> AgentStatus:
        """Check a single agent by ID.

        Tries ``<agent_id>.jsonl`` then ``<agent_id>.output`` in the output dir.
        Reads only the last 16KB of the file (tail-like) for efficiency.

        Args:
            agent_id: Agent identifier (file basename without extension).

        Returns:
            AgentStatus for the agent.
        """
        filepath = self._resolve_path(agent_id)

        if filepath is None:
            return AgentStatus(
                agent_id=agent_id,
                tool_call_count=0,
                last_activity_ts=0.0,
                last_progress_marker=None,
                last_assistant_text=None,
                file_size_bytes=0,
                status="unknown",
            )

        return self._status_from_file(agent_id, filepath)

    def _resolve_path(self, agent_id: str) -> Optional[str]:
        """Find the output file for an agent_id."""
        for ext in (".jsonl", ".output"):
            candidate = os.path.join(self.output_dir, agent_id + ext)
            if os.path.exists(candidate):
                return candidate
        return None

    def _status_from_file(self, agent_id: str, filepath: str) -> AgentStatus:
        """Build AgentStatus by reading the tail of a file."""
        try:
            stat = os.stat(filepath)
            file_size = stat.st_size
            last_activity_ts = stat.st_mtime
        except OSError:
            return AgentStatus(
                agent_id=agent_id,
                tool_call_count=0,
                last_activity_ts=0.0,
                last_progress_marker=None,
                last_assistant_text=None,
                file_size_bytes=0,
                status="unknown",
            )

        lines = _read_tail(filepath)
        tool_call_count, last_progress_marker, last_assistant_text = _parse_lines(lines)

        # For tool_call_count we need to read the FULL file when tail might miss early calls.
        # However, for large-file efficiency we only count what's in the tail window.
        # To get the total count we do a separate full scan — but only the count, so it's cheap.
        full_count = self._count_tool_calls_full(filepath)
        if full_count > tool_call_count:
            tool_call_count = full_count

        status = _derive_status(file_size, last_activity_ts, tool_call_count)
        step, total = _parse_progress_fields(last_progress_marker)

        return AgentStatus(
            agent_id=agent_id,
            tool_call_count=tool_call_count,
            last_activity_ts=last_activity_ts,
            last_progress_marker=last_progress_marker,
            last_assistant_text=last_assistant_text,
            file_size_bytes=file_size,
            status=status,
            progress_step=step,
            progress_total=total,
        )

    def _count_tool_calls_full(self, filepath: str) -> int:
        """Count tool_use blocks across entire file (efficient line-by-line scan)."""
        count = 0
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    if obj.get("type") != "assistant":
                        continue
                    content = obj.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                count += 1
        except OSError:
            pass
        return count

    def check_all(self) -> list[AgentStatus]:
        """Check all output files in the output directory.

        Returns:
            List of AgentStatus objects, one per file found.
        """
        statuses: list[AgentStatus] = []
        for filepath in self._output_files():
            agent_id = self._agent_id_from_path(filepath)
            statuses.append(self._status_from_file(agent_id, filepath))
        return statuses

    def format_dashboard(self) -> str:
        """Return a multi-line dashboard string showing all agent statuses.

        Format:
            AGENT DASHBOARD (3 running):
              abc: step 3/5 | 23 tools | 12s ago
              def: step 1/3 | 8 tools | 45s ago
              ghi: no markers | 15 tools | 3s ago

        Returns:
            Formatted dashboard string. Returns a no-agents message if directory
            is empty or doesn't exist.
        """
        statuses = self.check_all()

        if not statuses:
            return "AGENT DASHBOARD (0 running):\n  (no agent output files found)"

        running_count = sum(1 for s in statuses if s.status == "running")
        lines = ["AGENT DASHBOARD (%d running):" % running_count]

        for s in sorted(statuses, key=lambda x: x.agent_id):
            if s.progress_step is not None and s.progress_total is not None:
                progress_str = "step %d/%d" % (s.progress_step, s.progress_total)
            elif s.last_progress_marker:
                # Trim to something readable
                progress_str = s.last_progress_marker[:40]
            else:
                progress_str = "no markers"

            age = s.seconds_since_activity
            if age == float("inf"):
                age_str = "unknown"
            elif age < 60:
                age_str = "%ds ago" % int(age)
            elif age < 3600:
                age_str = "%dm ago" % int(age / 60)
            else:
                age_str = "%dh ago" % int(age / 3600)

            lines.append(
                "  %s [%s]: %s | %d tools | %s"
                % (s.agent_id, s.status, progress_str, s.tool_call_count, age_str)
            )

        return "\n".join(lines)


def poll_agents(output_dir: str) -> str:
    """Convenience function: check all agents in output_dir and return dashboard.

    Args:
        output_dir: Directory containing agent JSONL/output files.

    Returns:
        Formatted dashboard string.
    """
    return AgentOutputMonitor(output_dir).format_dashboard()
