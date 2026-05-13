# SCOPE: os-only
"""Anchored Summarizer — proactive context preservation before compaction.

Extracts critical context (decisions, file paths, task state) from conversation
text and saves it as a structured anchor document for post-compaction recovery.

Author: luum
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Patterns for extraction
# ---------------------------------------------------------------------------

_DECISION_PATTERNS = [
    r"(?:decided?\s+to|chose|will\s+use|approach\s*[:—]|decision\s*[:—]|using|we\s+(?:will|are)\s+(?:use|using))\s+(.+?)(?:[.\n]|$)",
    r"(?:chose|selected|picked|went\s+with)\s+(.+?)(?:[.\n]|$)",
    r"(?:the\s+approach\s+is|strategy\s+is|pattern\s+is)\s*[:—]?\s*(.+?)(?:[.\n]|$)",
]

_FILE_PATH_PATTERN = re.compile(
    r"""
    (?:
        # Unix-style paths with at least one directory separator
        (?:[a-zA-Z0-9_\-\.]+/)+[a-zA-Z0-9_\-\.]+(?:\.[a-zA-Z]{1,6})?
        |
        # Absolute paths
        /(?:[a-zA-Z0-9_\-\.]+/)*[a-zA-Z0-9_\-\.]+(?:\.[a-zA-Z]{1,6})?
    )
    """,
    re.VERBOSE,
)

_TASK_DONE_PATTERNS = [
    r"(?:completed?|finished?|done|implemented?|created?|added?|fixed?)\s*[:—]?\s*(.+?)(?:[.\n]|$)",
    r"(?:successfully\s+(?:completed?|implemented?|created?|added?))\s+(.+?)(?:[.\n]|$)",
]

_TASK_REMAINING_PATTERNS = [
    r"(?:still\s+need\s+to|remaining\s*[:—]?|next\s+(?:step|task|up)\s*[:—]?|todo\s*[:—]?)\s*(.+?)(?:[.\n]|$)",
    r"(?:haven't\s+yet|not\s+yet\s+(?:done|completed?|implemented?))\s*[:—]?\s*(.+?)(?:[.\n]|$)",
]

# Paths to exclude (noise)
_EXCLUDE_PATH_PREFIXES = (
    "http://",
    "https://",
    "ftp://",
    "//",
)
_EXCLUDE_PATH_WORDS = {
    "e.g.", "i.e.", "etc.", "vs.", "e.g", "i.e", "fig.", "ref.",
    "e.g", "N/A", "n/a", "TBD", "tbd",
}


class AnchoredSummarizer:
    """Proactive context preservation before compaction.

    Extracts decisions, file paths, and task state from conversation text,
    then persists them to a session file and/or Engram for post-compaction recovery.
    """

    def __init__(self, session_dir: str = ".cognitive-os/sessions/current") -> None:
        self._session_dir = Path(session_dir)

    # ------------------------------------------------------------------
    # Extraction methods
    # ------------------------------------------------------------------

    def extract_decisions(self, context_text: str) -> list[str]:
        """Extract architectural/design decisions from conversation text.

        Searches for common decision-signalling phrases and returns the
        extracted decision strings, deduplicated and trimmed.
        """
        if not context_text or not context_text.strip():
            return []

        found: list[str] = []
        for pattern in _DECISION_PATTERNS:
            for match in re.finditer(pattern, context_text, re.IGNORECASE):
                decision = match.group(1).strip().rstrip(".,;:")
                if decision and len(decision) > 3:
                    found.append(decision)

        # Deduplicate while preserving order
        seen: set[str] = set()
        result: list[str] = []
        for d in found:
            key = d.lower()
            if key not in seen:
                seen.add(key)
                result.append(d)
        return result

    def extract_file_paths(self, context_text: str) -> list[str]:
        """Extract file paths mentioned in conversation text.

        Returns a deduplicated list of plausible file/directory paths.
        Noise (URLs, single words) is filtered out.
        """
        if not context_text or not context_text.strip():
            return []

        raw_matches = _FILE_PATH_PATTERN.findall(context_text)

        seen: set[str] = set()
        result: list[str] = []
        for path in raw_matches:
            # Skip URLs and obvious noise
            if any(path.startswith(p) for p in _EXCLUDE_PATH_PREFIXES):
                continue
            if path in _EXCLUDE_PATH_WORDS:
                continue
            # Must contain a dot or slash to be a plausible path
            if "/" not in path and "." not in path:
                continue
            # Skip very short matches
            if len(path) < 5:
                continue
            if path not in seen:
                seen.add(path)
                result.append(path)

        return result

    def extract_task_state(self, context_text: str) -> dict[str, list[str]]:
        """Extract current task progress from conversation text.

        Returns a dict with keys 'done' and 'remaining', each containing
        a list of task descriptions extracted from the text.
        """
        if not context_text or not context_text.strip():
            return {"done": [], "remaining": []}

        done: list[str] = []
        remaining: list[str] = []

        for pattern in _TASK_DONE_PATTERNS:
            for match in re.finditer(pattern, context_text, re.IGNORECASE):
                item = match.group(1).strip().rstrip(".,;:")
                if item and len(item) > 3:
                    done.append(item)

        for pattern in _TASK_REMAINING_PATTERNS:
            for match in re.finditer(pattern, context_text, re.IGNORECASE):
                item = match.group(1).strip().rstrip(".,;:")
                if item and len(item) > 3:
                    remaining.append(item)

        # Deduplicate
        def dedup(items: list[str]) -> list[str]:
            seen: set[str] = set()
            result: list[str] = []
            for i in items:
                k = i.lower()
                if k not in seen:
                    seen.add(k)
                    result.append(i)
            return result

        return {"done": dedup(done), "remaining": dedup(remaining)}

    # ------------------------------------------------------------------
    # Anchor creation
    # ------------------------------------------------------------------

    def create_anchor(self, context_text: str) -> dict[str, Any]:
        """Create a full anchor document combining all extractions.

        Returns a structured dict ready to be persisted.
        """
        decisions = self.extract_decisions(context_text)
        files_touched = self.extract_file_paths(context_text)
        task_state = self.extract_task_state(context_text)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decisions": decisions,
            "files_touched": files_touched,
            "task_state": task_state,
            "summary": self._generate_summary(context_text, decisions, files_touched, task_state),
        }

    def _generate_summary(
        self,
        context_text: str,
        decisions: list[str],
        files_touched: list[str],
        task_state: dict[str, list[str]],
    ) -> str:
        """Generate a compact human-readable summary from extracted data."""
        lines: list[str] = []

        if decisions:
            lines.append("DECISIONS:")
            for d in decisions[:10]:  # Cap to avoid bloat
                lines.append(f"  - {d}")

        if files_touched:
            lines.append("FILES TOUCHED:")
            for f in files_touched[:20]:
                lines.append(f"  - {f}")

        done = task_state.get("done", [])
        remaining = task_state.get("remaining", [])

        if done:
            lines.append("COMPLETED:")
            for item in done[:10]:
                lines.append(f"  - {item}")

        if remaining:
            lines.append("REMAINING:")
            for item in remaining[:10]:
                lines.append(f"  - {item}")

        if not lines:
            # Fallback: first 500 chars of context as summary
            stripped = context_text.strip()
            if stripped:
                lines.append(stripped[:500] + ("..." if len(stripped) > 500 else ""))

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def persist_anchor(
        self,
        anchor: dict[str, Any],
        to_file: bool = True,
        to_engram: bool = True,
    ) -> dict[str, Any]:
        """Save anchor to session file and optionally to Engram.

        Returns a dict with keys:
          - 'file_path': path written (or None if to_file=False)
          - 'engram_saved': bool
        """
        file_path: str | None = None
        engram_saved = False

        if to_file:
            self._session_dir.mkdir(parents=True, exist_ok=True)
            anchor_file = self._session_dir / "anchor.json"
            anchor_file.write_text(json.dumps(anchor, indent=2, ensure_ascii=False))
            file_path = str(anchor_file)

        if to_engram:
            engram_saved = self._save_to_engram(anchor)

        return {"file_path": file_path, "engram_saved": engram_saved}

    def _save_to_engram(self, anchor: dict[str, Any]) -> bool:
        """Attempt to save anchor to Engram via CLI. Returns True on success."""
        try:
            content = json.dumps(anchor, indent=2, ensure_ascii=False)
            ts = anchor.get("timestamp", "")
            title = "Pre-compaction anchor " + ts
            script = (
                "import sys, os; sys.path.insert(0, os.getcwd()); "
                "from lib.safe_engram import safe_mem_save; "
                "safe_mem_save("
                "title=" + repr(title) + ", "
                "topic_key='session/anchor', "
                "type='discovery', "
                "scope='project', "
                "content=" + repr(content) + ")"
            )
            result = subprocess.run(
                ["python3", "-c", script],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.returncode == 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Class-level convenience
    # ------------------------------------------------------------------

    @classmethod
    def auto_save(cls, session_dir: str = ".cognitive-os/sessions/current") -> dict[str, Any]:
        """Convenience method: extract from recent state and persist.

        Reads the current session's state snapshot (if present) or falls back
        to an empty context, then creates and persists an anchor.

        Called by hooks (e.g. pre-compaction-flush.sh).

        Returns the persist_anchor result dict.
        """
        instance = cls(session_dir=session_dir)
        session_path = Path(session_dir)

        # Try to read existing state snapshot for richer context
        context_text = ""
        snapshot_file = session_path / "state-snapshot.json"
        if snapshot_file.exists():
            try:
                snapshot = json.loads(snapshot_file.read_text())
                context_text = json.dumps(snapshot, indent=2)
            except Exception:
                pass

        # Also try conversation capture file
        conversation_file = session_path / "conversation-capture.jsonl"
        if conversation_file.exists() and conversation_file.stat().st_size < 500_000:
            try:
                lines = conversation_file.read_text().splitlines()
                # Only last 200 lines to keep it tractable
                recent = "\n".join(lines[-200:])
                context_text = (context_text + "\n" + recent).strip()
            except Exception:
                pass

        anchor = instance.create_anchor(context_text)
        return instance.persist_anchor(anchor, to_file=True, to_engram=False)
