"""tool_use_correlation — Pre/Post event timing correlation (ADR-033b).

Claude Code hook payloads carry ``tool_use_id`` in both PreToolUse and
PostToolUse events but do NOT include a ``started_at`` timestamp in the Post
payload. This module bridges the gap:

- On ``PreToolUse:Agent`` — record ``{tool_use_id: monotonic_time}``
- On ``PostToolUse:Agent`` — pop the recorded time, return elapsed milliseconds

The store is backed by an in-memory dict **plus** a JSONL file for crash
recovery across processes (e.g. if a Pre hook fires in one Python process and
a Post hook fires in a fresh Python process 30 s later).

TTL: entries older than ``ttl_seconds`` (default 3600 s) are pruned on each
``record`` call to prevent unbounded growth.

Usage::

    from lib.harness_adapter.tool_use_correlation import CorrelationStore

    store = CorrelationStore()            # reads/writes default persistence path
    store.record("abc123", time.monotonic())
    duration = store.pop("abc123")        # float (seconds since record) or None
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, Optional

_DEFAULT_PATH = ".cognitive-os/metrics/tool-use-correlation.jsonl"
_TTL_SECONDS = 3600  # 1 hour


class CorrelationStore:
    """Thread-safe (per-process) mapping from tool_use_id to start time.

    Crash recovery is provided by a JSONL persistence file. On construction the
    file is replayed into memory; on each ``record`` the new entry is appended
    (upsert semantics: the file grows; stale entries are pruned in-memory only).
    """

    def __init__(
        self,
        persistence_path: Optional[Path] = None,
        ttl_seconds: float = _TTL_SECONDS,
        project_dir: Optional[Path] = None,
    ) -> None:
        if persistence_path is not None:
            self._path = Path(persistence_path)
        else:
            root = Path(project_dir) if project_dir else Path(
                os.environ.get("COGNITIVE_OS_PROJECT_DIR")
                or os.environ.get("CLAUDE_PROJECT_DIR")
                or "."
            )
            self._path = root / _DEFAULT_PATH
        self._ttl = ttl_seconds
        self._store: Dict[str, float] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, tool_use_id: str, started_at: float) -> None:
        """Store *started_at* for *tool_use_id* and persist it.

        ``started_at`` should be a monotonic clock value (``time.monotonic()``)
        or a wall-clock float; the caller is responsible for consistency.
        The value returned by :meth:`pop` is the raw stored float — compute
        ``duration_ms = (now - started_at) * 1000`` after popping.
        """
        if not tool_use_id:
            return
        self._prune()
        self._store[tool_use_id] = started_at
        self._append(tool_use_id, started_at)

    def pop(self, tool_use_id: str) -> Optional[float]:
        """Return and remove the stored start time for *tool_use_id*.

        Returns ``None`` if the ID is unknown or has been pruned.
        """
        if not tool_use_id:
            return None
        return self._store.pop(tool_use_id, None)

    def get(self, tool_use_id: str) -> Optional[float]:
        """Return the stored start time without removing it."""
        return self._store.get(tool_use_id)

    def __len__(self) -> int:
        return len(self._store)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _append(self, tool_use_id: str, started_at: float) -> None:
        """Append one record to the JSONL file (best-effort; failures are silent)."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            entry = json.dumps(
                {"tool_use_id": tool_use_id, "started_at": started_at},
                sort_keys=True,
            )
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(entry + "\n")
        except Exception:
            pass

    def _load(self) -> None:
        """Replay the persistence file into memory (last-write-wins per ID)."""
        if not self._path.exists():
            return
        cutoff = time.monotonic() - self._ttl
        try:
            with open(self._path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        tid = rec.get("tool_use_id", "")
                        ts = float(rec.get("started_at", 0))
                        if tid and ts > cutoff:
                            self._store[tid] = ts
                    except (json.JSONDecodeError, ValueError, TypeError):
                        continue
        except OSError:
            pass

    def _prune(self) -> None:
        """Remove in-memory entries older than TTL."""
        cutoff = time.monotonic() - self._ttl
        stale = [k for k, v in self._store.items() if v <= cutoff]
        for k in stale:
            del self._store[k]
