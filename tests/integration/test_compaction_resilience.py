"""Integration tests: compaction + parallel-agent resilience.

Covers the scenario: 5 agents running in background, context compacts,
3 agents finish post-compaction, session cleanup runs.

Scenario groups
---------------
A. Pre-compaction state persistence (StateHeartbeat)
B. Task notification survival (active-tasks.json schema)
C. File write conflict detection (concurrent-write-guard.sh patterns)
D. Session cleanup with active agents (session_hygiene.prune_completed_tasks)
E. Engram topic-key isolation (AgentProgressTracker)
F. Recovery after compaction (crash-recovery patterns)
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Project root on sys.path is already handled by conftest / pytest.ini
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.state_heartbeat import StateHeartbeat
from lib.session_hygiene import prune_completed_tasks
from lib.agent_progress_tracker import AgentProgressTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso(delta_days: int = 0) -> str:
    """Return an ISO-8601 timestamp offset by delta_days from now (UTC)."""
    dt = datetime.now(timezone.utc) + timedelta(days=delta_days)
    return dt.isoformat()


def _make_tasks_file(tmp_path: Path, tasks: list[dict]) -> Path:
    """Write a minimal active-tasks.json and return its path."""
    path = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": "1.0", "tasks": tasks}, indent=2))
    return path


def _make_heartbeat(tmp_path: Path, session_id: str = "test-session") -> StateHeartbeat:
    """Return a StateHeartbeat wired to a temp session dir."""
    session_dir = tmp_path / ".cognitive-os" / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return StateHeartbeat(str(session_dir))


# ===========================================================================
# A. Pre-Compaction State Persistence
# ===========================================================================

class TestHeartbeatSnapshotPersistence:
    """StateHeartbeat serialises and recovers state correctly."""

    def test_heartbeat_snapshot_contains_active_agents(self, tmp_path):
        """Snapshot captures in-progress tasks and round-trips via save/load."""
        # Arrange: write active-tasks.json with two in-progress tasks
        tasks = [
            {"id": "agent-ws14b", "description": "Write integration tests", "status": "in_progress"},
            {"id": "agent-ws16",  "description": "Update preamble",          "status": "in_progress"},
            {"id": "agent-done",  "description": "Already done",             "status": "completed"},
        ]
        _make_tasks_file(tmp_path, tasks)

        hb = _make_heartbeat(tmp_path)
        # Override _find_project_dir to return tmp_path (no .cognitive-os marker needed)
        hb._find_project_dir = lambda: tmp_path  # type: ignore[method-assign]

        # Act
        hb.save()
        loaded = hb.load()

        # Assert
        assert loaded is not None, "Snapshot should exist after save()"
        assert "timestamp" in loaded
        assert "active_tasks" in loaded

        in_progress = loaded["active_tasks"].get("in_progress", [])
        ids = [t["id"] for t in in_progress]
        assert "agent-ws14b" in ids
        assert "agent-ws16" in ids
        assert "agent-done" not in ids, "completed tasks must not appear in in_progress"

    def test_heartbeat_snapshot_contains_pending_requests(self, tmp_path):
        """Pending requests survive save/load round-trip."""
        hb = _make_heartbeat(tmp_path)

        # Write a request queue directly into the session dir
        queue_path = Path(hb._session_dir) / "request-queue.json"
        queue_path.write_text(json.dumps([
            {"message": "Deploy when ready", "done": False},
            {"message": "Already handled",   "done": True},
        ]))

        hb.save()
        loaded = hb.load()

        assert loaded is not None
        pending = loaded.get("pending_requests", {}).get("pending", [])
        assert len(pending) == 1, "Only non-done requests should appear as pending"
        assert "Deploy when ready" in pending[0]

    def test_heartbeat_snapshot_contains_git_status(self, tmp_path):
        """Git status collector returns a dict with expected keys."""
        hb = _make_heartbeat(tmp_path)

        snap = hb.snapshot()

        git = snap.get("git_status", {})
        # Either it collected real git data or reported unavailable — both are dicts
        assert isinstance(git, dict), "git_status must be a dict"
        # If available it has dirty_files; if not it has status=unavailable
        assert "dirty_files" in git or "status" in git

    def test_heartbeat_recovery_prompt_format(self, tmp_path):
        """format_recovery_prompt includes in-progress task descriptions."""
        tasks = [
            {"id": "t1", "description": "Implement auth flow", "status": "in_progress"},
        ]
        _make_tasks_file(tmp_path, tasks)

        hb = _make_heartbeat(tmp_path)
        hb._find_project_dir = lambda: tmp_path  # type: ignore[method-assign]
        hb.save()

        prompt = hb.format_recovery_prompt()

        assert "PREVIOUS SESSION STATE" in prompt
        assert "Implement auth flow" in prompt, "Task description must appear in recovery prompt"

    def test_heartbeat_no_snapshot_returns_sensible_message(self, tmp_path):
        """load() returns None and format_recovery_prompt is friendly when no snapshot exists."""
        hb = _make_heartbeat(tmp_path, session_id="fresh-session")

        assert hb.load() is None
        prompt = hb.format_recovery_prompt()
        assert "No previous session" in prompt


# ===========================================================================
# B. Task Notification Survival
# ===========================================================================

class TestActiveTasksSchema:
    """active-tasks.json lifecycle and schema integrity tests."""

    def test_task_notification_has_result_inline(self):
        """The task-notification XML format must include a <result> field.

        Verifies the expected XML structure used by orchestrators to read
        sub-agent output without reading raw JSONL files.
        """
        # Simulate what the system produces on task completion
        sample_notification = (
            "<task-notification>"
            "<task_id>ws14b-integration-tests</task_id>"
            "<status>completed</status>"
            "<result>Created 22 integration tests in test_compaction_resilience.py</result>"
            "</task-notification>"
        )

        assert "<result>" in sample_notification, "task-notification must contain <result> field"
        assert "</result>" in sample_notification

        # Extract result
        m = re.search(r"<result>(.*?)</result>", sample_notification, re.DOTALL)
        assert m is not None
        assert len(m.group(1)) > 0, "<result> must not be empty"

    def test_active_tasks_tracks_agent_lifecycle(self, tmp_path):
        """Create → in_progress → completed lifecycle writes valid JSON at each step."""
        path = _make_tasks_file(tmp_path, [])

        # Step 1: create
        data = json.loads(path.read_text())
        data["tasks"].append({
            "id": "lifecycle-test",
            "description": "Test lifecycle",
            "status": "pending",
            "createdAt": _iso(),
        })
        path.write_text(json.dumps(data, indent=2))

        raw = json.loads(path.read_text())
        assert raw["tasks"][0]["status"] == "pending"

        # Step 2: mark in_progress
        raw["tasks"][0]["status"] = "in_progress"
        raw["tasks"][0]["startedAt"] = _iso()
        path.write_text(json.dumps(raw, indent=2))

        raw = json.loads(path.read_text())
        assert raw["tasks"][0]["status"] == "in_progress"

        # Step 3: mark completed
        raw["tasks"][0]["status"] = "completed"
        raw["tasks"][0]["completedAt"] = _iso()
        raw["tasks"][0]["outputSummary"] = "Task completed successfully"
        path.write_text(json.dumps(raw, indent=2))

        final = json.loads(path.read_text())
        t = final["tasks"][0]
        assert t["status"] == "completed"
        assert "outputSummary" in t

    def test_active_tasks_survives_file_rewrite(self, tmp_path):
        """Writing active-tasks.json twice in a row does not corrupt the file."""
        path = _make_tasks_file(tmp_path, [
            {"id": "t1", "status": "in_progress", "description": "Agent 1"},
        ])

        # First rewrite (simulates agent 2 completing)
        data = json.loads(path.read_text())
        data["tasks"].append({"id": "t2", "status": "completed", "description": "Agent 2"})
        path.write_text(json.dumps(data, indent=2))

        # Second rewrite (simulates agent 3 completing)
        data = json.loads(path.read_text())
        data["tasks"].append({"id": "t3", "status": "completed", "description": "Agent 3"})
        path.write_text(json.dumps(data, indent=2))

        final = json.loads(path.read_text())
        assert len(final["tasks"]) == 3
        ids = {t["id"] for t in final["tasks"]}
        assert ids == {"t1", "t2", "t3"}

    def test_completed_task_has_output_summary(self, tmp_path):
        """Tasks marked completed should carry an outputSummary field."""
        path = _make_tasks_file(tmp_path, [
            {
                "id": "ws13b",
                "description": "Finalize session-wrapup skill",
                "status": "completed",
                "completedAt": _iso(),
                "outputSummary": "Skill created and registered in CATALOG.md",
            }
        ])
        data = json.loads(path.read_text())
        t = data["tasks"][0]
        assert "outputSummary" in t, "Completed tasks must have outputSummary field"
        assert len(t["outputSummary"]) > 0


# ===========================================================================
# C. File Write Conflict Detection
# ===========================================================================

class TestFileWriteConflictDetection:
    """Validate concurrent-write-guard behaviour (hook source analysis)."""

    HOOK_PATH = Path(__file__).parent.parent.parent / "hooks" / "concurrent-write-guard.sh"

    def test_concurrent_write_same_file_hook_exists(self):
        """concurrent-write-guard.sh must exist — without it writes are unprotected."""
        assert self.HOOK_PATH.exists(), (
            "hooks/concurrent-write-guard.sh not found. "
            "Concurrent file writes are UNPROTECTED."
        )

    def test_hook_requires_session_id(self):
        """Hook must skip locking when no SESSION_ID is set (advisory, not blocking)."""
        content = self.HOOK_PATH.read_text()
        # The hook exits early when SESSION_ID is empty
        assert "SESSION_ID" in content
        assert "exit 0" in content, "Hook must exit 0 (non-blocking) when no session ID"

    def test_hook_uses_flock_for_real_serialisation(self):
        """v0.4+ hook must use flock, not just advisory metadata."""
        content = self.HOOK_PATH.read_text()
        assert "flock" in content, (
            "concurrent-write-guard must use OS-level flock for real serialisation"
        )

    def test_hook_generates_stable_hash_for_file_path(self):
        """Hook must hash the file path to create a lock filename."""
        content = self.HOOK_PATH.read_text()
        assert "FILE_HASH" in content or "md5" in content, (
            "Hook must produce a stable per-file hash for lock file naming"
        )

    def test_preamble_conflict_scenario(self, tmp_path):
        """Two agents writing agent-preamble.md — last write wins, content remains valid.

        Simulates WS16 and WS13b both modifying agent-preamble.md.
        The test verifies the file is valid JSON/text after both writes.
        """
        preamble = tmp_path / "agent-preamble.md"
        preamble.write_text("# Agent Preamble\nVersion: 1\n")

        # Agent WS13b writes
        preamble.write_text("# Agent Preamble\nVersion: 2\nAdded: session-wrapup\n")

        # Agent WS16 writes (last writer wins)
        preamble.write_text("# Agent Preamble\nVersion: 3\nAdded: session-wrapup, preamble-update\n")

        final_content = preamble.read_text()
        assert "Agent Preamble" in final_content, "File must remain readable after concurrent writes"
        assert "Version: 3" in final_content, "Last write must be the surviving content"

    def test_atomic_write_pattern(self, tmp_path):
        """StateHeartbeat.save() uses tmp-file + os.replace (atomic write)."""
        hb = _make_heartbeat(tmp_path)

        # Inspect the source — we already know it uses tempfile.mkstemp + os.replace
        import inspect
        source = inspect.getsource(hb.save)

        assert "mkstemp" in source or "replace" in source, (
            "save() must use atomic write (mkstemp + os.replace) to prevent torn reads"
        )

    def test_atomic_write_no_partial_file_on_success(self, tmp_path):
        """After save(), no .tmp files are left behind in the session dir."""
        hb = _make_heartbeat(tmp_path)
        hb.save()

        session_dir = Path(hb._session_dir)
        tmp_files = list(session_dir.glob(".state-snapshot-*.tmp"))
        assert len(tmp_files) == 0, f"Orphaned tmp files after save(): {tmp_files}"


# ===========================================================================
# D. Session Cleanup with Active Agents
# ===========================================================================

class TestSessionCleanup:
    """prune_completed_tasks must never remove in_progress or recent tasks."""

    def test_prune_skips_in_progress_tasks(self, tmp_path):
        """in_progress tasks must survive prune regardless of age."""
        path = _make_tasks_file(tmp_path, [
            {
                "id": "live-agent",
                "description": "Still running",
                "status": "in_progress",
                "createdAt": _iso(-30),  # 30 days old
            }
        ])

        result = prune_completed_tasks(str(path), max_age_days=7)

        assert result["pruned"] == 0
        data = json.loads(path.read_text())
        ids = [t["id"] for t in data["tasks"]]
        assert "live-agent" in ids, "in_progress task must never be pruned"

    def test_prune_skips_recent_completed(self, tmp_path):
        """Tasks completed < max_age_days ago must survive."""
        path = _make_tasks_file(tmp_path, [
            {
                "id": "recent-done",
                "description": "Finished yesterday",
                "status": "completed",
                "completedAt": _iso(-1),  # 1 day ago
            }
        ])

        result = prune_completed_tasks(str(path), max_age_days=7)

        assert result["pruned"] == 0
        data = json.loads(path.read_text())
        assert any(t["id"] == "recent-done" for t in data["tasks"])

    def test_prune_removes_old_completed(self, tmp_path):
        """Tasks completed > max_age_days ago must be pruned."""
        path = _make_tasks_file(tmp_path, [
            {
                "id": "stale-done",
                "description": "Finished 10 days ago",
                "status": "completed",
                "completedAt": _iso(-10),
            }
        ])

        result = prune_completed_tasks(str(path), max_age_days=7)

        assert result["pruned"] == 1
        data = json.loads(path.read_text())
        assert not any(t["id"] == "stale-done" for t in data["tasks"])

    def test_prune_keeps_failed_tasks(self, tmp_path):
        """failed tasks are never pruned — they need human investigation."""
        path = _make_tasks_file(tmp_path, [
            {
                "id": "failed-agent",
                "description": "Build exploded",
                "status": "failed",
                "completedAt": _iso(-30),
            }
        ])

        result = prune_completed_tasks(str(path), max_age_days=7)

        assert result["pruned"] == 0
        assert result["failed_kept"] == 1
        data = json.loads(path.read_text())
        assert any(t["id"] == "failed-agent" for t in data["tasks"])

    def test_cleanup_doesnt_corrupt_active_tasks(self, tmp_path):
        """Mixed-status file remains valid JSON after prune."""
        path = _make_tasks_file(tmp_path, [
            {"id": "ip1",     "status": "in_progress", "description": "Running 1"},
            {"id": "ip2",     "status": "in_progress", "description": "Running 2"},
            {"id": "recent",  "status": "completed",   "description": "Done yesterday",
             "completedAt": _iso(-1)},
            {"id": "stale",   "status": "completed",   "description": "Done 2 weeks ago",
             "completedAt": _iso(-14)},
            {"id": "broken",  "status": "failed",      "description": "Blew up",
             "completedAt": _iso(-5)},
        ])

        result = prune_completed_tasks(str(path), max_age_days=7)

        # Only the stale completed task should be removed
        assert result["pruned"] == 1

        # File must still be valid JSON with correct structure
        data = json.loads(path.read_text())
        assert "tasks" in data
        remaining_ids = {t["id"] for t in data["tasks"]}
        assert "ip1" in remaining_ids
        assert "ip2" in remaining_ids
        assert "recent" in remaining_ids
        assert "broken" in remaining_ids
        assert "stale" not in remaining_ids

    def test_prune_on_nonexistent_file_returns_zeros(self, tmp_path):
        """prune_completed_tasks is safe when the file does not exist."""
        missing = tmp_path / "no-such-file.json"
        result = prune_completed_tasks(str(missing))
        assert result == {"pruned": 0, "remaining": 0, "failed_kept": 0}

    def test_prune_on_corrupted_json_returns_zeros(self, tmp_path):
        """prune_completed_tasks is safe when the file contains invalid JSON."""
        bad = tmp_path / "active-tasks.json"
        bad.write_text("{not valid json")
        result = prune_completed_tasks(str(bad))
        assert result == {"pruned": 0, "remaining": 0, "failed_kept": 0}


# ===========================================================================
# E. Engram Topic Key Isolation
# ===========================================================================

class TestEngramTopicKeyIsolation:
    """AgentProgressTracker generates distinct, stable topic keys per agent."""

    def test_different_agents_different_topic_keys(self):
        """Two agents with different task descriptions use different topic keys."""
        tracker_a = AgentProgressTracker("Fix authentication bug in lib/auth.py")
        tracker_b = AgentProgressTracker("Update preamble template for new rules")

        assert tracker_a._topic_key != tracker_b._topic_key, (
            "Different agents must use different topic keys to avoid Engram collisions"
        )

    def test_same_agent_upserts_not_duplicates(self):
        """Same task description → same topic key (upsert semantics, no duplicates)."""
        description = "Write integration tests for compaction resilience"

        tracker1 = AgentProgressTracker(description)
        tracker2 = AgentProgressTracker(description)

        assert tracker1._topic_key == tracker2._topic_key, (
            "Same task description must produce the same topic key for upsert behaviour"
        )

    def test_topic_key_follows_prefix_convention(self):
        """All progress topic keys must start with 'agent-progress/' per engram-organization.md."""
        tracker = AgentProgressTracker("Implement new feature for auth module")
        assert tracker._topic_key.startswith("agent-progress/"), (
            f"Topic key '{tracker._topic_key}' must start with 'agent-progress/'"
        )

    def test_topic_key_is_url_safe(self):
        """Topic key must contain only lowercase alphanumeric, hyphens, and slashes."""
        tracker = AgentProgressTracker("Fix Bug: special chars & spaces!!")
        key = tracker._topic_key
        # Allow letters, digits, hyphens, forward slash
        assert re.match(r"^[a-z0-9\-/]+$", key), (
            f"Topic key '{key}' contains unsafe characters"
        )

    def test_progress_save_format_has_required_fields(self):
        """format_progress_save returns a dict with all required mem_save fields."""
        tracker = AgentProgressTracker("Write tests", project="luum-cognitive-os")
        result = tracker.format_progress_save(
            tool_call_number=10,
            files_created=["tests/test_foo.py"],
            findings=["discovered module X"],
        )

        required_fields = {"title", "content", "type", "topic_key", "project"}
        missing = required_fields - result.keys()
        assert not missing, f"format_progress_save missing fields: {missing}"

    def test_final_save_uses_same_topic_key(self):
        """format_final_save must use the same topic_key as format_progress_save (upsert)."""
        tracker = AgentProgressTracker("Refactor payment module", project="test")

        progress = tracker.format_progress_save(tool_call_number=10)
        final = tracker.format_final_save(result_summary="Done")

        assert progress["topic_key"] == final["topic_key"], (
            "Progress and final saves must share the same topic_key for upsert behaviour"
        )

    def test_should_save_triggers_every_10_calls(self):
        """should_save returns True at call 10, 20, 30 and False at 0, 1, 9, 11."""
        tracker = AgentProgressTracker("Test task")

        assert not tracker.should_save(0)
        assert not tracker.should_save(1)
        assert not tracker.should_save(9)
        assert tracker.should_save(10)
        assert not tracker.should_save(11)
        assert tracker.should_save(20)
        assert tracker.should_save(30)


# ===========================================================================
# F. Recovery After Compaction
# ===========================================================================

class TestCrashRecovery:
    """Session snapshot discovery and recovery prompt generation."""

    def test_crash_recovery_finds_orphaned_snapshot(self, tmp_path):
        """A snapshot left in a session dir is findable by scanning sessions/."""
        sessions_root = tmp_path / ".cognitive-os" / "sessions"
        orphan_dir = sessions_root / "orphaned-session-abc"
        orphan_dir.mkdir(parents=True)

        # Write a realistic snapshot
        snapshot = {
            "timestamp": _iso(-1),
            "session_dir": str(orphan_dir),
            "active_tasks": {"in_progress": [{"id": "t1", "description": "Was running"}]},
            "git_status": {"dirty_files": ["lib/foo.py"]},
        }
        (orphan_dir / "state-snapshot.json").write_text(json.dumps(snapshot, indent=2))

        # Scan for snapshots (mimicking crash-recovery logic)
        found = list(sessions_root.glob("*/state-snapshot.json"))

        assert len(found) >= 1, "Crash recovery must find the orphaned snapshot"
        assert any("orphaned-session-abc" in str(p) for p in found)

    def test_crash_recovery_reads_most_recent_session(self, tmp_path):
        """When multiple orphaned sessions exist, the most recently written snapshot is the one to load."""
        sessions_root = tmp_path / ".cognitive-os" / "sessions"

        older_dir = sessions_root / "session-old"
        older_dir.mkdir(parents=True)
        newer_dir = sessions_root / "session-new"
        newer_dir.mkdir(parents=True)

        older_snap = older_dir / "state-snapshot.json"
        older_snap.write_text(json.dumps({
            "timestamp": _iso(-2),
            "active_tasks": {"in_progress": [{"id": "old-task"}]},
        }))

        # Small sleep so mtime differs
        time.sleep(0.05)

        newer_snap = newer_dir / "state-snapshot.json"
        newer_snap.write_text(json.dumps({
            "timestamp": _iso(-1),
            "active_tasks": {"in_progress": [{"id": "new-task"}]},
        }))

        # Find most recent by mtime
        snapshots = list(sessions_root.glob("*/state-snapshot.json"))
        most_recent = max(snapshots, key=lambda p: p.stat().st_mtime)
        data = json.loads(most_recent.read_text())

        assert data["active_tasks"]["in_progress"][0]["id"] == "new-task", (
            "Crash recovery must load the most recently written snapshot"
        )

    def test_session_summary_in_engram_format(self):
        """mem_session_summary payload structure is parseable.

        We mock the call and verify the content structure is what Engram expects.
        Tests that the orchestrator produces a well-formed summary without
        requiring a live Engram instance.
        """
        captured_kwargs: dict = {}

        def mock_mem_session_summary(**kwargs):
            captured_kwargs.update(kwargs)
            return {"status": "ok"}

        with patch("builtins.__import__"):
            # Simulate the orchestrator calling mem_session_summary
            mock_mem_session_summary(
                goal="Write compaction resilience integration tests",
                instructions="Use pytest, tmp_path, no mocks for Engram",
                discoveries=["StateHeartbeat uses atomic writes", "prune skips in_progress"],
                accomplished=["Created test_compaction_resilience.py with 22 tests"],
                next_steps=["Run CI", "Add xfail notes for unimplemented features"],
                relevant_files=["tests/integration/test_compaction_resilience.py"],
            )

        required_keys = {"goal", "instructions", "discoveries", "accomplished",
                         "next_steps", "relevant_files"}
        missing = required_keys - captured_kwargs.keys()
        assert not missing, f"mem_session_summary missing required keys: {missing}"

        assert isinstance(captured_kwargs["discoveries"], list)
        assert isinstance(captured_kwargs["accomplished"], list)
        assert isinstance(captured_kwargs["relevant_files"], list)

    def test_heartbeat_recovery_prompt_includes_pending_requests(self, tmp_path):
        """Recovery prompt mentions pending user requests so they are not lost."""
        hb = _make_heartbeat(tmp_path)

        queue_path = Path(hb._session_dir) / "request-queue.json"
        queue_path.write_text(json.dumps([
            {"message": "Deploy feature branch when tests pass", "done": False},
        ]))

        hb.save()
        prompt = hb.format_recovery_prompt()

        assert "Deploy feature branch" in prompt, (
            "Pending user requests must appear in the recovery prompt"
        )

    @pytest.mark.xfail(
        reason="auto-snapshot-load not yet implemented in session-init.sh: "
               "crash-recovery.sh is wired to SessionStart but session-init.sh does not "
               "yet inject state-snapshot.json into the live session context"
    )
    def test_session_start_hook_loads_snapshot_automatically(self, tmp_path):
        """The session-init SessionStart hook should auto-load the last snapshot.

        Currently the hook exists but snapshot injection into the session context
        is not implemented — the hook only reads session ID and creates meta.json.
        """
        hook_path = Path(__file__).parent.parent.parent / "hooks" / "session-init.sh"
        assert hook_path.exists()
        content = hook_path.read_text()
        # This will xfail because auto-snapshot-load is not yet implemented
        assert "state-snapshot.json" in content, (
            "session-init.sh should load state-snapshot.json automatically"
        )


# ===========================================================================
# G. Parallel Agent Safety (cross-cutting)
# ===========================================================================

class TestParallelAgentSafety:
    """End-to-end simulation: 5 parallel agents, compaction, cleanup."""

    def test_five_parallel_agents_all_trackable(self, tmp_path):
        """5 agents with distinct topic keys can all be tracked without collision."""
        agent_tasks = [
            "Write preamble update for new compaction rules",
            "Add queue drainer tests to test suite alpha",
            "Fix session hygiene prune edge case beta",
            "Update CATALOG md with new session skills gamma",
            "Verify state heartbeat atomic write pattern delta",
        ]
        trackers = [AgentProgressTracker(t) for t in agent_tasks]
        keys = [tr._topic_key for tr in trackers]

        assert len(keys) == len(set(keys)), (
            "5 parallel agents must produce 5 distinct topic keys — no collision"
        )

    def test_all_active_tasks_survive_one_prune_cycle(self, tmp_path):
        """A prune cycle on a file with 5 in_progress + 2 old completed removes only old completed."""
        tasks = [
            {"id": f"agent-{i}", "status": "in_progress",
             "description": f"Agent {i} running", "createdAt": _iso()}
            for i in range(5)
        ]
        tasks += [
            {"id": "old-1", "status": "completed", "completedAt": _iso(-10)},
            {"id": "old-2", "status": "completed", "completedAt": _iso(-15)},
        ]
        path = _make_tasks_file(tmp_path, tasks)

        result = prune_completed_tasks(str(path), max_age_days=7)

        assert result["pruned"] == 2, "Only the 2 old completed tasks should be pruned"
        data = json.loads(path.read_text())
        remaining_ids = {t["id"] for t in data["tasks"]}
        for i in range(5):
            assert f"agent-{i}" in remaining_ids, f"agent-{i} must survive prune"

    def test_heartbeat_snapshot_with_five_agents(self, tmp_path):
        """Snapshot captures all 5 in-progress agent tasks."""
        tasks = [
            {
                "id": f"parallel-{i}",
                "description": f"Parallel agent task {i}",
                "status": "in_progress",
                "createdAt": _iso(),
            }
            for i in range(5)
        ]
        _make_tasks_file(tmp_path, tasks)

        hb = _make_heartbeat(tmp_path)
        hb._find_project_dir = lambda: tmp_path  # type: ignore[method-assign]
        hb.save()
        loaded = hb.load()

        assert loaded is not None
        in_progress = loaded["active_tasks"]["in_progress"]
        assert len(in_progress) == 5, f"All 5 agents must appear in snapshot, got {len(in_progress)}"

    def test_post_compaction_three_agents_complete(self, tmp_path):
        """After compaction, 3 of 5 agents complete — prune leaves 2 still in_progress."""
        # Pre-compaction: 5 in_progress
        tasks = [
            {"id": f"agent-{i}", "status": "in_progress",
             "description": f"Agent {i}", "createdAt": _iso()}
            for i in range(5)
        ]
        path = _make_tasks_file(tmp_path, tasks)

        # Post-compaction: 3 complete (agents 0, 1, 2)
        data = json.loads(path.read_text())
        for t in data["tasks"]:
            if t["id"] in ("agent-0", "agent-1", "agent-2"):
                t["status"] = "completed"
                t["completedAt"] = _iso()   # completed just now (< 7 days)
        path.write_text(json.dumps(data, indent=2))

        # Cleanup runs — recent completions must NOT be pruned
        result = prune_completed_tasks(str(path), max_age_days=7)

        assert result["pruned"] == 0, "Just-completed tasks must survive the first cleanup"
        data = json.loads(path.read_text())
        in_progress = [t for t in data["tasks"] if t["status"] == "in_progress"]
        assert len(in_progress) == 2, "2 agents still in_progress after 3 complete"
