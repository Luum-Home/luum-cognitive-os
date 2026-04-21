"""anchored_summary.py — Structured session anchor for context-compaction recovery.

AnchoredSummary maintains a rolling structured summary of the most important
information from agent messages: decisions made, file paths touched, and task
state. The anchor is updated incrementally and can be persisted to Engram for
cross-compaction recovery.

stdlib only — no external dependencies.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional


# ---------------------------------------------------------------------------
# Regex patterns for extraction (compiled once at module level)
# ---------------------------------------------------------------------------

_FILE_PATTERN = re.compile(
    r"""
    (?:
        [\w./\-]+/[\w.\-]+\.(?:go|py|ts|js|tsx|jsx|java|yaml|yml|json|sh|md|txt|sql|proto|toml|cfg|ini|env)
        |
        \b\w+\.(?:go|py|ts|js|tsx|jsx|java|yaml|yml|json|sh|md|txt|sql|proto|toml|cfg|ini|env)\b
    )
    """,
    re.VERBOSE,
)

_DECISION_PATTERNS = [
    re.compile(r"Decision(?::|—|-)\s*(.+?)(?:\.|$)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"decided\s+to\s+(.+?)(?:\.|$)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"using\s+(\w[\w\s]+)\s+(?:for|as|instead)", re.IGNORECASE),
    re.compile(r"will\s+use\s+(.+?)(?:\.|$)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"chose\s+(.+?)(?:\.|$)", re.IGNORECASE | re.MULTILINE),
]

_TASK_STATE_PATTERNS = [
    re.compile(r"(?:completed?|done|finished)\s*:?\s*(.+?)(?:\.|$)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"(?:in progress|working on|implementing)\s*:?\s*(.+?)(?:\.|$)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"(?:next step|todo|TODO|remaining)\s*:?\s*(.+?)(?:\.|$)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"PROGRESS:\s*(.+?)(?:\.|$)", re.MULTILINE),
]


def _extract_text(content: Any) -> str:
    """Safely extract text from a message content field."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Handle Anthropic content block list format
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts)
    return str(content)


@dataclass
class AnchoredSummary:
    """Rolling structured summary of agent session state.

    Accumulates decisions, file paths, and task state across iterative merges.
    Designed to survive context compaction — state persists via Engram.

    Usage::

        anchor = AnchoredSummary()
        anchor.merge_new_messages(messages)
        summary = anchor.get_summary()
        anchor.save_to_engram("session-key")
        loaded = AnchoredSummary.load_from_engram("session-key")
    """

    decisions: list[str] = field(default_factory=list)
    file_paths: list[str] = field(default_factory=list)
    task_state: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    raw_excerpts: list[str] = field(default_factory=list)

    # Limits to prevent unbounded growth
    _MAX_DECISIONS: ClassVar[int] = 50
    _MAX_FILES: ClassVar[int] = 100
    _MAX_TASK_STATES: ClassVar[int] = 30
    _MAX_EXCERPTS: ClassVar[int] = 20
    _MAX_EXCERPT_LEN: ClassVar[int] = 200

    # ---------------------------------------------------------------------------
    # Core merge
    # ---------------------------------------------------------------------------

    def merge_new_messages(self, messages: list[dict[str, Any]]) -> None:
        """Update the anchor by processing new messages.

        Messages are dicts with at least a ``role`` key. ``content`` may be
        a string, list of content blocks, or None (tool-call-only messages).

        Args:
            messages: List of message dicts. Empty list is a no-op.
        """
        if not messages:
            return

        for msg in messages:
            if not isinstance(msg, dict):
                continue

            role = msg.get("role", "")
            content = _extract_text(msg.get("content"))

            if not content:
                # Tool-call-only message — nothing to extract
                continue

            # Only process assistant messages for structured extraction;
            # user messages are ignored to reduce noise.
            if role == "assistant":
                self._extract_decisions(content)
                self._extract_file_paths(content)
                self._extract_task_state(content)
                self._store_excerpt(content)

    # ---------------------------------------------------------------------------
    # Extraction helpers
    # ---------------------------------------------------------------------------

    def _extract_decisions(self, text: str) -> None:
        """Extract decision statements from text."""
        for pattern in _DECISION_PATTERNS:
            for match in pattern.finditer(text):
                decision = match.group(1).strip()
                if decision and len(decision) > 3 and decision not in self.decisions:
                    self.decisions.append(decision)
                    if len(self.decisions) > self._MAX_DECISIONS:
                        self.decisions.pop(0)

    def _extract_file_paths(self, text: str) -> None:
        """Extract file path references from text."""
        for match in _FILE_PATTERN.finditer(text):
            path = match.group(0).strip()
            if path and path not in self.file_paths:
                self.file_paths.append(path)
                if len(self.file_paths) > self._MAX_FILES:
                    self.file_paths.pop(0)

    def _extract_task_state(self, text: str) -> None:
        """Extract task state statements from text."""
        for pattern in _TASK_STATE_PATTERNS:
            for match in pattern.finditer(text):
                state = match.group(1).strip()
                if state and len(state) > 3 and state not in self.task_state:
                    self.task_state.append(state)
                    if len(self.task_state) > self._MAX_TASK_STATES:
                        self.task_state.pop(0)

    def _store_excerpt(self, text: str) -> None:
        """Store a short excerpt of significant assistant output."""
        excerpt = text[: self._MAX_EXCERPT_LEN].strip()
        if excerpt and excerpt not in self.raw_excerpts:
            self.raw_excerpts.append(excerpt)
            if len(self.raw_excerpts) > self._MAX_EXCERPTS:
                self.raw_excerpts.pop(0)

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------

    def get_summary(self) -> dict[str, Any]:
        """Return a structured summary dict of the current anchor state.

        Returns:
            Dict with keys: decisions, file_paths, task_state, next_steps,
            raw_excerpts.  All values are lists.  The dict is deterministic
            given the same anchor state.
        """
        return {
            "decisions": list(self.decisions),
            "file_paths": list(self.file_paths),
            "task_state": list(self.task_state),
            "next_steps": list(self.next_steps),
            "raw_excerpts": list(self.raw_excerpts),
        }

    # ---------------------------------------------------------------------------
    # Engram persistence
    # ---------------------------------------------------------------------------

    def save_to_engram(self, session_key: str) -> bool:
        """Persist the anchor to Engram under ``session_key``.

        Serialises anchor state as JSON and saves it via the ``engram`` CLI
        (``engram save <title> <content>``).  Silently returns ``False`` if
        Engram is not available rather than raising.

        Args:
            session_key: Stable key used as both the observation title and
                the search term for retrieval.

        Returns:
            True if saved successfully, False otherwise.
        """
        payload = json.dumps(self.get_summary(), ensure_ascii=False)
        # Title embeds a sentinel prefix so search can find it unambiguously.
        title = f"anchored-summary::{session_key}"
        try:
            result = subprocess.run(
                [
                    "engram", "save", title, payload,
                    "--type", "architecture",
                    "--project", "luum-cognitive-os",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    @classmethod
    def load_from_engram(cls, session_key: str) -> Optional["AnchoredSummary"]:
        """Load an anchor from Engram by ``session_key``.

        Searches for the observation saved by :meth:`save_to_engram` and
        parses its JSON content.

        Args:
            session_key: The key passed to :meth:`save_to_engram`.

        Returns:
            A new :class:`AnchoredSummary` instance populated with the saved
            state, or ``None`` if loading fails.
        """
        search_title = f"anchored-summary::{session_key}"
        try:
            result = subprocess.run(
                ["engram", "search", search_title, "--limit", "1"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None

            # The engram search output contains the observation content.
            # We look for the JSON payload embedded in the output.
            output = result.stdout
            # Find the first '{' ... '}' JSON block in the output.
            json_start = output.find("{")
            json_end = output.rfind("}") + 1
            if json_start == -1 or json_end <= json_start:
                return None
            data = json.loads(output[json_start:json_end])

            anchor = cls()
            anchor.decisions = data.get("decisions", [])
            anchor.file_paths = data.get("file_paths", [])
            anchor.task_state = data.get("task_state", [])
            anchor.next_steps = data.get("next_steps", [])
            anchor.raw_excerpts = data.get("raw_excerpts", [])
            return anchor
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
            return None

    # ---------------------------------------------------------------------------
    # Convenience
    # ---------------------------------------------------------------------------

    def __bool__(self) -> bool:
        """Return True if the anchor has any content."""
        return bool(
            self.decisions
            or self.file_paths
            or self.task_state
            or self.next_steps
            or self.raw_excerpts
        )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"AnchoredSummary("
            f"decisions={len(self.decisions)}, "
            f"file_paths={len(self.file_paths)}, "
            f"task_state={len(self.task_state)})"
        )
