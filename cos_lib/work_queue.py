# SCOPE: both
"""Persistent work queue that survives across sessions.

Reads/writes .cognitive-os/work-queue.json. Auto-updated at session end
by session-hygiene.sh hook. The orchestrator reads this at session start
to know exactly what's pending.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


class WorkQueue:
    """Persistent cross-session work queue."""

    def __init__(self, queue_path: str = ".cognitive-os/work-queue.json"):
        self._path = queue_path
        self._data = self._load()

    def _load(self) -> dict:
        try:
            with open(self._path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"version": 1, "last_updated": "", "priority_queue": [],
                    "user_concerns": [], "completed_this_sprint": []}

    def _save(self):
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        tmp = self._path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self._path)

    def get_pending(self) -> list[dict]:
        """All pending tasks, sorted by priority."""
        return sorted(
            [t for t in self._data.get("priority_queue", []) if t.get("status") == "pending"],
            key=lambda t: t.get("priority", 99)
        )

    def get_next(self) -> dict | None:
        """Highest priority pending task with met dependencies."""
        completed_ids = {t["id"] for t in self._data.get("priority_queue", [])
                        if t.get("status") == "completed"}
        for task in self.get_pending():
            deps = set(task.get("depends_on", []))
            if deps.issubset(completed_ids):
                return task
        return None

    def complete_task(self, task_id: str, summary: str = ""):
        """Mark a task as completed."""
        for task in self._data.get("priority_queue", []):
            if task["id"] == task_id:
                task["status"] = "completed"
                task["completed_at"] = datetime.now(timezone.utc).isoformat()
                if summary:
                    task["completion_summary"] = summary
                break
        self._data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._save()

    def add_task(self, task_id: str, description: str, priority: int = 3,
                 depends_on: list[str] | None = None, estimated_effort: str = "",
                 context: str = ""):
        """Add a new task. Skips if ID already exists."""
        existing_ids = {t["id"] for t in self._data.get("priority_queue", [])}
        if task_id in existing_ids:
            return False
        self._data.setdefault("priority_queue", []).append({
            "id": task_id,
            "description": description,
            "priority": priority,
            "status": "pending",
            "depends_on": depends_on or [],
            "estimated_effort": estimated_effort,
            "context": context,
            "added_at": datetime.now(timezone.utc).isoformat()
        })
        self._data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._save()
        return True

    def add_concern(self, concern: str):
        """Add a user concern if not already present."""
        concerns = self._data.setdefault("user_concerns", [])
        if concern not in concerns:
            concerns.append(concern)
            self._save()

    def get_concerns(self) -> list[str]:
        return self._data.get("user_concerns", [])

    def record_completion(self, description: str):
        """Record something completed this sprint."""
        completed = self._data.setdefault("completed_this_sprint", [])
        if description not in completed:
            completed.append(description)
            self._save()

    def sync_from_plans(self, plans_dir: str = ".cognitive-os/plans/features"):
        """Read plan files and update task statuses based on plan Status headers."""
        import re
        if not os.path.isdir(plans_dir):
            return 0
        updated = 0
        for fname in os.listdir(plans_dir):
            if not fname.endswith(".md"):
                continue
            try:
                with open(os.path.join(plans_dir, fname)) as f:
                    head = f.read(500)
                match = re.search(r'\*\*Status\*\*:\s*(\w+)', head)
                if match and match.group(1).upper() == "COMPLETED":
                    slug = fname.replace(".md", "")
                    for task in self._data.get("priority_queue", []):
                        if slug in task["id"] and task["status"] == "pending":
                            task["status"] = "completed"
                            task["completed_at"] = datetime.now(timezone.utc).isoformat()
                            task["completion_summary"] = "Auto-detected from plan status"
                            updated += 1
            except (OSError, UnicodeDecodeError):
                continue
        if updated:
            self._save()
        return updated

    def format_session_brief(self) -> str:
        """Format a brief for the next session's orchestrator."""
        pending = self.get_pending()
        next_task = self.get_next()
        concerns = self.get_concerns()

        lines = ["=== WORK QUEUE BRIEF ==="]
        lines.append(f"Pending: {len(pending)} tasks")
        if next_task:
            lines.append(f"Next: [{next_task['id']}] {next_task['description']}")
            if next_task.get("context"):
                lines.append(f"  Context: {next_task['context'][:200]}")
        lines.append("")
        if concerns:
            lines.append("USER CONCERNS:")
            for c in concerns[:5]:
                lines.append(f"  - {c}")
            lines.append("")
        lines.append("FULL QUEUE:")
        for t in pending[:10]:
            deps = f" (blocked by: {', '.join(t.get('depends_on', []))})" if t.get("depends_on") else ""
            lines.append(f"  P{t.get('priority', '?')}: [{t['id']}] {t['description']}{deps}")
        if len(pending) > 10:
            lines.append(f"  ... and {len(pending) - 10} more")
        lines.append("========================")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return self._data
