# SCOPE: os-only
"""Checkpoint Manager -- periodic WAL-like saves for crash recovery.

Creates named git stashes at regular intervals so uncommitted work survives
crashes, power loss, OOM kills, and network failures.  Python 3.9+ compatible,
stdlib only.

Author: luum
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Checkpoint:
    """Immutable record of a single checkpoint."""

    checkpoint_id: str
    timestamp: str
    git_stash_ref: Optional[str]  # git stash reference if dirty files
    session_id: str
    tasks_in_progress: List[str]
    files_modified: List[str]
    uncommitted_changes: int  # count of dirty files
    engram_saves_pending: int
    cost_since_last_commit: float
    note: str


class CheckpointManager:
    """Periodic checkpoint system -- like a database WAL for the OS.

    Every N minutes (default 5), saves:
    1. Git stash of uncommitted changes (recoverable)
    2. Session state (what was being done)
    3. List of modified files
    4. Cost accumulated since last commit
    """

    def __init__(
        self,
        checkpoint_dir: str = ".cognitive-os/checkpoints",
        interval_minutes: int = 5,
        project_dir: Optional[str] = None,
    ):
        self.project_dir = project_dir or os.environ.get(
            "CLAUDE_PROJECT_DIR", os.getcwd()
        )
        self.checkpoint_dir = os.path.join(self.project_dir, checkpoint_dir)
        self.interval_minutes = interval_minutes

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_git(self, *args: str) -> subprocess.CompletedProcess:
        """Run a git command in the project directory."""
        return subprocess.run(
            ["git"] + list(args),
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def _dirty_files(self) -> List[str]:
        """Return list of uncommitted (dirty) file paths."""
        result = self._run_git("status", "--porcelain")
        if result.returncode != 0:
            return []
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        # Each line has a 2-char status prefix followed by a space and the path
        files = []
        for line in lines:
            # Handle renames: "R  old -> new"
            parts = line[3:]
            if " -> " in parts:
                parts = parts.split(" -> ")[-1]
            files.append(parts.strip())
        return files

    def _generate_id(self) -> str:
        """Generate a unique checkpoint ID."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        # Add a short hash to avoid collisions within the same second
        entropy = hashlib.md5(
            f"{ts}-{os.getpid()}-{time.monotonic_ns()}".encode()
        ).hexdigest()[:6]
        return f"cos-{ts}-{entropy}"

    def _now_iso(self) -> str:
        """Return current UTC time in ISO-8601 format."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _load_tasks_in_progress(self) -> List[str]:
        """Read in-progress tasks from active-tasks.json."""
        tasks_file = os.path.join(
            self.project_dir, ".cognitive-os", "tasks", "active-tasks.json"
        )
        if not os.path.isfile(tasks_file):
            return []
        try:
            with open(tasks_file, "r") as f:
                data = json.load(f)
            return [
                t.get("description", t.get("id", "unknown"))
                for t in data.get("tasks", [])
                if t.get("status") == "in_progress"
            ]
        except (json.JSONDecodeError, OSError):
            return []

    def _read_cost_since_last_commit(self) -> float:
        """Estimate cost since last commit from cost-events.jsonl."""
        cost_file = os.path.join(
            self.project_dir, ".cognitive-os", "metrics", "cost-events.jsonl"
        )
        if not os.path.isfile(cost_file):
            return 0.0

        # Get last commit timestamp
        result = self._run_git("log", "-1", "--format=%aI")
        if result.returncode != 0 or not result.stdout.strip():
            return 0.0

        try:
            last_commit_ts = result.stdout.strip()
            total = 0.0
            with open(cost_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        ts = entry.get("timestamp", "")
                        if ts > last_commit_ts:
                            total += entry.get("estimated_cost_usd", 0.0)
                    except json.JSONDecodeError:
                        continue
            return round(total, 4)
        except OSError:
            return 0.0

    def _marker_path(self) -> str:
        """Path to the last-checkpoint timestamp marker."""
        return os.path.join(self.checkpoint_dir, ".last-checkpoint")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_checkpoint(self, note: str = "periodic") -> Checkpoint:
        """Create a checkpoint NOW.

        Steps:
        1. git status -> list dirty files
        2. If dirty: git stash push -m "cos-checkpoint-{id}"
                     then git stash pop (keep changes, but stash is saved)
        3. Save checkpoint metadata to checkpoints/{id}.json
        4. Save session state snapshot
        5. Return checkpoint object

        NOTE: git stash push + pop means the stash exists as a backup
        but working directory is unchanged. If crash happens, the stash
        survives because it is in .git/refs/stash.
        """
        os.makedirs(self.checkpoint_dir, exist_ok=True)

        checkpoint_id = self._generate_id()
        dirty = self._dirty_files()
        stash_ref: Optional[str] = None

        if dirty:
            # Create a named stash (survives crashes)
            stash_msg = checkpoint_id
            stash_result = self._run_git(
                "stash", "push", "-m", stash_msg, "--include-untracked"
            )
            if stash_result.returncode == 0 and "No local changes" not in stash_result.stdout:
                stash_ref = stash_msg
                # Pop immediately to restore working directory
                self._run_git("stash", "pop")

        session_id = os.environ.get("COGNITIVE_OS_SESSION_ID", "unknown")
        tasks = self._load_tasks_in_progress()
        cost = self._read_cost_since_last_commit()

        cp = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=self._now_iso(),
            git_stash_ref=stash_ref,
            session_id=session_id,
            tasks_in_progress=tasks,
            files_modified=dirty,
            uncommitted_changes=len(dirty),
            engram_saves_pending=0,
            cost_since_last_commit=cost,
            note=note,
        )

        # Save checkpoint metadata
        meta_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
        self._write_json(meta_path, asdict(cp))

        # Update marker
        marker = self._marker_path()
        with open(marker, "w") as f:
            f.write(str(int(time.time())))

        return cp

    def recover_from_crash(self) -> Optional[Dict[str, Any]]:
        """Called at session start. Checks for crash indicators:

        1. Check .cognitive-os/checkpoints/ for recent checkpoints
        2. Check git stash list for cos-checkpoint-* entries
        3. Check if last session ended cleanly (session-cleanup ran?)
        4. If crash detected:
           - List what was being worked on
           - List uncommitted changes available in stash
           - Suggest recovery actions

        Returns None if no crash detected.
        Returns Dict with recovery info if crash found.
        """
        # Check for cos- stashes
        stash_result = self._run_git("stash", "list")
        cos_stashes: List[Dict[str, str]] = []
        if stash_result.returncode == 0 and stash_result.stdout.strip():
            for line in stash_result.stdout.strip().splitlines():
                if "cos-" in line:
                    cos_stashes.append({"entry": line.strip()})

        if not cos_stashes:
            return None

        # Check if last session ended cleanly
        cleanup_marker = os.path.join(
            self.project_dir, ".cognitive-os", "sessions", ".last-cleanup"
        )
        last_cleanup: Optional[str] = None
        if os.path.isfile(cleanup_marker):
            try:
                with open(cleanup_marker, "r") as f:
                    last_cleanup = f.read().strip()
            except OSError:
                pass

        # Load the most recent checkpoint metadata
        checkpoints = self.list_checkpoints(last_n=1)
        last_checkpoint: Optional[Dict[str, Any]] = None
        if checkpoints:
            last_checkpoint = asdict(checkpoints[0])

        # Determine crash time estimate
        crash_time_estimate: Optional[str] = None
        if last_checkpoint:
            crash_time_estimate = last_checkpoint.get("timestamp")

        recovery_info: Dict[str, Any] = {
            "crash_detected": True,
            "last_clean_session": last_cleanup,
            "crash_time_estimate": crash_time_estimate,
            "stashes": cos_stashes,
            "stash_count": len(cos_stashes),
            "last_checkpoint": last_checkpoint,
            "tasks_in_progress": (
                last_checkpoint.get("tasks_in_progress", []) if last_checkpoint else []
            ),
            "files_modified": (
                last_checkpoint.get("files_modified", []) if last_checkpoint else []
            ),
            "cost_since_last_commit": (
                last_checkpoint.get("cost_since_last_commit", 0.0)
                if last_checkpoint
                else 0.0
            ),
        }

        return recovery_info

    def restore_stash(self, checkpoint_id: str) -> bool:
        """Restore a specific checkpoint's stash.

        Searches git stash list for the matching checkpoint_id and applies it.
        """
        stash_result = self._run_git("stash", "list")
        if stash_result.returncode != 0:
            return False

        for line in stash_result.stdout.strip().splitlines():
            if checkpoint_id in line:
                # Extract stash ref (e.g., stash@{0})
                stash_ref = line.split(":")[0].strip()
                apply_result = self._run_git("stash", "apply", stash_ref)
                return apply_result.returncode == 0

        return False

    def list_checkpoints(self, last_n: int = 5) -> List[Checkpoint]:
        """List recent checkpoints sorted by timestamp (newest first)."""
        if not os.path.isdir(self.checkpoint_dir):
            return []

        checkpoint_files = []
        for fname in os.listdir(self.checkpoint_dir):
            if fname.startswith("cos-") and fname.endswith(".json"):
                checkpoint_files.append(
                    os.path.join(self.checkpoint_dir, fname)
                )

        # Sort by modification time, newest first
        checkpoint_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)

        results: List[Checkpoint] = []
        for path in checkpoint_files[:last_n]:
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                results.append(
                    Checkpoint(
                        checkpoint_id=data.get("checkpoint_id", ""),
                        timestamp=data.get("timestamp", ""),
                        git_stash_ref=data.get("git_stash_ref"),
                        session_id=data.get("session_id", ""),
                        tasks_in_progress=data.get("tasks_in_progress", []),
                        files_modified=data.get("files_modified", []),
                        uncommitted_changes=data.get("uncommitted_changes", 0),
                        engram_saves_pending=data.get("engram_saves_pending", 0),
                        cost_since_last_commit=data.get(
                            "cost_since_last_commit", 0.0
                        ),
                        note=data.get("note", ""),
                    )
                )
            except (json.JSONDecodeError, OSError, KeyError):
                continue

        return results

    def cleanup_old_checkpoints(self, keep_last: int = 10) -> int:
        """Remove old checkpoint files (keep stashes for git gc).

        Returns the number of checkpoint files removed.
        """
        if not os.path.isdir(self.checkpoint_dir):
            return 0

        checkpoint_files = []
        for fname in os.listdir(self.checkpoint_dir):
            if fname.startswith("cos-") and fname.endswith(".json"):
                full = os.path.join(self.checkpoint_dir, fname)
                checkpoint_files.append(full)

        # Sort by mtime, newest first
        checkpoint_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)

        to_remove = checkpoint_files[keep_last:]
        removed = 0
        for path in to_remove:
            try:
                os.unlink(path)
                removed += 1
            except OSError:
                pass

        return removed

    def should_checkpoint(
        self, last_checkpoint_time: Optional[datetime] = None
    ) -> bool:
        """Check if enough time has passed for a new checkpoint."""
        if last_checkpoint_time is not None:
            now = datetime.now(timezone.utc)
            elapsed = (now - last_checkpoint_time).total_seconds()
            return elapsed >= self.interval_minutes * 60

        # Check marker file
        marker = self._marker_path()
        if not os.path.isfile(marker):
            return True

        try:
            with open(marker, "r") as f:
                last_ts = int(f.read().strip())
            return (int(time.time()) - last_ts) >= self.interval_minutes * 60
        except (ValueError, OSError):
            return True

    def format_recovery_report(self, recovery_info: Dict[str, Any]) -> str:
        """Format crash recovery info for display."""
        lines: List[str] = []
        lines.append("")
        lines.append("WARNING: CRASH RECOVERY DETECTED")
        lines.append("")

        last_clean = recovery_info.get("last_clean_session", "unknown")
        crash_est = recovery_info.get("crash_time_estimate", "unknown")
        lines.append(f"  Last clean session: {last_clean}")
        lines.append(f"  Crash time (estimated): {crash_est}")
        lines.append("")

        lines.append("  Recoverable work:")

        files = recovery_info.get("files_modified", [])
        if files:
            lines.append(
                f"  +-- {len(files)} uncommitted file(s) (in git stash)"
            )
            for f in files:
                lines.append(f"  |   +-- {f}")

        tasks = recovery_info.get("tasks_in_progress", [])
        if tasks:
            lines.append(f"  +-- {len(tasks)} task(s) were in progress")
            for t in tasks:
                lines.append(f"  |   +-- {t}")

        cost = recovery_info.get("cost_since_last_commit", 0.0)
        if cost > 0:
            lines.append(f"  +-- ${cost:.2f} in tokens spent since last commit")

        lines.append("")
        lines.append("  Actions:")

        stashes = recovery_info.get("stashes", [])
        if stashes:
            lines.append("  1. Restore stashed files: git stash apply")
            lines.append("  2. Resume tasks: /resume-tasks")
            lines.append("  3. Discard and start fresh: git stash drop")
        else:
            lines.append("  1. Resume tasks: /resume-tasks")

        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _write_json(path: str, data: Dict[str, Any]) -> None:
        """Write JSON atomically via temp file + rename."""
        dir_name = os.path.dirname(path)
        os.makedirs(dir_name, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=dir_name, suffix=".tmp", prefix=".checkpoint-"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


def auto_checkpoint_hook_logic(project_dir: Optional[str] = None) -> None:
    """Logic for the periodic checkpoint hook.

    Called by the hook every N tool uses to check if checkpoint needed.
    """
    mgr = CheckpointManager(project_dir=project_dir)
    if mgr.should_checkpoint():
        dirty = mgr._dirty_files()
        if dirty:
            mgr.create_checkpoint(note="periodic")
        else:
            # No dirty files -- just update the marker
            os.makedirs(mgr.checkpoint_dir, exist_ok=True)
            marker = mgr._marker_path()
            with open(marker, "w") as f:
                f.write(str(int(time.time())))
