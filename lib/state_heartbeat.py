# SCOPE: both
"""State Heartbeat — continuous session state persistence.

Runs a set of pluggable collectors every N tool calls (or every N seconds) and
writes a JSON snapshot to the session directory.  Any interruption (suspend,
crash, compaction) loses at most the work done since the last save.

Author: luum
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional


class StateHeartbeat:
    """Pluggable collector architecture for continuous state persistence."""

    def __init__(self, session_dir: str) -> None:
        """
        Args:
            session_dir: path to the current session directory,
                         e.g. .cognitive-os/sessions/{id}/
        """
        self._session_dir = Path(session_dir)
        self._session_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_path = self._session_dir / "state-snapshot.json"
        self._collectors: Dict[str, Callable[[], dict]] = {}

        # Register built-in collectors
        self.register("active_tasks", self._collect_active_tasks)
        self.register("pending_requests", self._collect_pending_requests)
        self.register("git_status", self._collect_git_status)
        self.register("session_meta", self._collect_session_meta)
        self.register("todo_state", self._collect_todo_state)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, name: str, collector: Callable[[], dict]) -> None:
        """Register a named state collector function."""
        self._collectors[name] = collector

    def snapshot(self) -> dict:
        """Run all collectors and return the combined state dict."""
        state: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_dir": str(self._session_dir),
        }
        for name, collector in self._collectors.items():
            try:
                result = collector()
                if not isinstance(result, dict):
                    result = {"value": result}
                state[name] = result
            except Exception as exc:  # noqa: BLE001
                state[name] = {"status": "unavailable", "error": str(exc)}
        return state

    def save(self) -> None:
        """Write a fresh snapshot to session_dir/state-snapshot.json (atomic)."""
        data = self.snapshot()
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=self._session_dir, prefix=".state-snapshot-", suffix=".tmp"
        )
        try:
            with os.fdopen(tmp_fd, "w") as fh:
                json.dump(data, fh, indent=2)
            os.replace(tmp_path, self._snapshot_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def load(self) -> Optional[dict]:
        """Read and return the last snapshot, or None if it does not exist."""
        try:
            with open(self._snapshot_path) as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def format_recovery_prompt(self) -> str:
        """Format the last snapshot as a recovery prompt for the next session."""
        data = self.load()
        if data is None:
            return "No previous session state found."

        lines = [
            "PREVIOUS SESSION STATE (recovery context):",
            f"  Snapshot taken: {data.get('timestamp', 'unknown')}",
        ]

        # Active tasks
        tasks = data.get("active_tasks", {})
        in_progress = tasks.get("in_progress", [])
        if in_progress:
            lines.append(f"  In-progress tasks ({len(in_progress)}):")
            for t in in_progress[:5]:
                desc = t.get("description", t.get("id", "unknown"))
                lines.append(f"    - {desc}")

        # Git status
        git = data.get("git_status", {})
        dirty = git.get("dirty_files", [])
        if dirty:
            lines.append(f"  Uncommitted files ({len(dirty)}):")
            for f in dirty[:5]:
                lines.append(f"    - {f}")

        # Pending requests
        pending = data.get("pending_requests", {}).get("pending", [])
        if pending:
            lines.append(f"  Pending user requests ({len(pending)}):")
            for r in pending[:3]:
                lines.append(f"    - {r}")

        # Todos
        todos = data.get("todo_state", {}).get("incomplete", [])
        if todos:
            lines.append(f"  Incomplete todos ({len(todos)}):")
            for td in todos[:5]:
                lines.append(f"    - {td}")

        lines.append("  Resume from where the previous session left off.")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Built-in collectors
    # ------------------------------------------------------------------

    def _collect_active_tasks(self) -> dict:
        """Read .cognitive-os/tasks/active-tasks.json, return in_progress tasks."""
        # Walk up from session_dir to find project root
        project_dir = self._find_project_dir()
        tasks_path = project_dir / ".cognitive-os" / "tasks" / "active-tasks.json"
        try:
            with open(tasks_path) as fh:
                data = json.load(fh)
            tasks = data.get("tasks", [])
            in_progress = [
                {"id": t.get("id"), "description": t.get("description"), "status": t.get("status")}
                for t in tasks
                if t.get("status") in ("in_progress", "running", "pending")
            ]
            return {"in_progress": in_progress, "total": len(tasks)}
        except FileNotFoundError:
            return {"status": "unavailable", "reason": "active-tasks.json not found"}
        except (json.JSONDecodeError, KeyError) as exc:
            return {"status": "unavailable", "error": str(exc)}

    def _collect_pending_requests(self) -> dict:
        """Read request queue from the session dir, return pending items."""
        queue_path = self._session_dir / "request-queue.json"
        try:
            with open(queue_path) as fh:
                data = json.load(fh)
            items = data if isinstance(data, list) else data.get("requests", [])
            pending = [
                r.get("message", r) if isinstance(r, dict) else r
                for r in items
                if not (isinstance(r, dict) and r.get("done"))
            ]
            return {"pending": pending, "total": len(items)}
        except FileNotFoundError:
            return {"pending": [], "total": 0}
        except (json.JSONDecodeError, KeyError) as exc:
            return {"status": "unavailable", "error": str(exc)}

    def _collect_git_status(self) -> dict:
        """Run git status --porcelain and return uncommitted files summary."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return {"status": "unavailable", "reason": "not a git repo"}
            lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
            return {"dirty_files": lines, "count": len(lines)}
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            return {"status": "unavailable", "error": str(exc)}

    def _collect_session_meta(self) -> dict:
        """Return session ID, start time, and working directory."""
        meta_path = self._session_dir / "meta.json"
        base: dict = {
            "session_dir": str(self._session_dir),
            "working_directory": os.getcwd(),
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with open(meta_path) as fh:
                meta = json.load(fh)
            base.update(meta)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return base

    def _collect_todo_state(self) -> dict:
        """Read todos.json from the session dir if it exists."""
        todos_path = self._session_dir / "todos.json"
        try:
            with open(todos_path) as fh:
                data = json.load(fh)
            todos = data if isinstance(data, list) else data.get("todos", [])
            incomplete = [
                t.get("content", t) if isinstance(t, dict) else t
                for t in todos
                if not (isinstance(t, dict) and t.get("status") == "completed")
            ]
            return {"incomplete": incomplete, "total": len(todos)}
        except FileNotFoundError:
            return {"incomplete": [], "total": 0}
        except (json.JSONDecodeError, KeyError) as exc:
            return {"status": "unavailable", "error": str(exc)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_project_dir(self) -> Path:
        """Walk up from session_dir to find the project root (contains .cognitive-os)."""
        candidate = self._session_dir
        for _ in range(10):
            if (candidate / ".cognitive-os").is_dir():
                return candidate
            parent = candidate.parent
            if parent == candidate:
                break
            candidate = parent
        # Fallback: assume session_dir is inside .cognitive-os/sessions/{id}/
        # so project root is 3 levels up
        return self._session_dir.parent.parent.parent
