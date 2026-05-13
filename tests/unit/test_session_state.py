"""Tests for lib/session_state.py — Session State Persistence.

Covers save/load roundtrip, agent lifecycle, pending tasks, checkpoint
updates, missing state files, atomic writes, and cross-session recovery.

Run with: pytest tests/unit/test_session_state.py -v
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lib.session_state import (
    _atomic_write,
    _empty_state,
    _state_path,
    add_pending_task,
    checkpoint,
    complete_pending_task,
    load_state,
    mark_agent_complete,
    record_agent,
    save_state,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    """Create a temporary .cognitive-os directory and return the project root."""
    cos_dir = tmp_path / ".cognitive-os"
    cos_dir.mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# load_state — missing / invalid
# ---------------------------------------------------------------------------


class TestLoadState:
    """Tests for load_state behavior."""

    def test_returns_none_when_no_file(self, state_dir: Path) -> None:
        """load_state returns None when session-state.json does not exist."""
        result = load_state(project_dir=str(state_dir))
        assert result is None

    def test_returns_none_for_invalid_json(self, state_dir: Path) -> None:
        """load_state returns None for corrupt JSON."""
        state_file = state_dir / ".cognitive-os" / "session-state.json"
        state_file.write_text("not valid json {{{")
        result = load_state(project_dir=str(state_dir))
        assert result is None

    def test_returns_none_for_missing_session_id(self, state_dir: Path) -> None:
        """load_state returns None if JSON lacks session_id key."""
        state_file = state_dir / ".cognitive-os" / "session-state.json"
        state_file.write_text(json.dumps({"agents": []}))
        result = load_state(project_dir=str(state_dir))
        assert result is None

    def test_returns_none_for_non_dict(self, state_dir: Path) -> None:
        """load_state returns None if JSON is a list, not a dict."""
        state_file = state_dir / ".cognitive-os" / "session-state.json"
        state_file.write_text(json.dumps([1, 2, 3]))
        result = load_state(project_dir=str(state_dir))
        assert result is None


# ---------------------------------------------------------------------------
# save_state / load_state roundtrip
# ---------------------------------------------------------------------------


class TestSaveLoadRoundtrip:
    """Tests for save_state and load_state working together."""

    def test_basic_roundtrip(self, state_dir: Path) -> None:
        """save_state followed by load_state returns the same data."""
        save_state(
            session_id="sess-001",
            agents=[{"id": "a1", "description": "test agent", "status": "running", "files_expected": ["f.py"], "files_created": []}],
            pending_tasks=["task-a", "task-b"],
            checkpoint_note="initial save",
            stats={"tests_passed": 42},
            project_dir=str(state_dir),
        )
        loaded = load_state(project_dir=str(state_dir))
        assert loaded is not None
        assert loaded["session_id"] == "sess-001"
        assert loaded["checkpoint_note"] == "initial save"
        assert loaded["pending_tasks"] == ["task-a", "task-b"]
        assert loaded["stats"]["tests_passed"] == 42
        assert len(loaded["agents"]) == 1
        assert loaded["agents"][0]["id"] == "a1"

    def test_preserves_completed_tasks_on_update(self, state_dir: Path) -> None:
        """save_state preserves completed_tasks when session_id matches."""
        save_state(session_id="sess-002", project_dir=str(state_dir))
        # Manually add a completed task
        add_pending_task("do-something", project_dir=str(state_dir))
        state = load_state(project_dir=str(state_dir))
        assert state is not None
        state["session_id"] = "sess-002"
        state["completed_tasks"] = ["done-task"]
        _atomic_write(_state_path(str(state_dir)), state)

        # Now save_state with same session_id should keep completed_tasks
        updated = save_state(
            session_id="sess-002",
            pending_tasks=["new-task"],
            project_dir=str(state_dir),
        )
        assert "done-task" in updated["completed_tasks"]

    def test_new_session_id_resets_completed_tasks(self, state_dir: Path) -> None:
        """save_state with a different session_id starts fresh."""
        save_state(session_id="old-session", project_dir=str(state_dir))
        state = load_state(project_dir=str(state_dir))
        assert state is not None
        state["completed_tasks"] = ["old-task"]
        _atomic_write(_state_path(str(state_dir)), state)

        # New session should not carry over old completed tasks
        new_state = save_state(session_id="new-session", project_dir=str(state_dir))
        assert new_state["completed_tasks"] == []

    def test_empty_args_creates_minimal_state(self, state_dir: Path) -> None:
        """save_state with only session_id creates valid minimal state."""
        saved = save_state(session_id="minimal", project_dir=str(state_dir))
        assert saved["session_id"] == "minimal"
        assert saved["agents"] == []
        assert saved["pending_tasks"] == []
        assert saved["completed_tasks"] == []
        assert saved["stats"] == {}


# ---------------------------------------------------------------------------
# record_agent + mark_agent_complete
# ---------------------------------------------------------------------------


class TestAgentLifecycle:
    """Tests for recording agents and marking them complete."""

    def test_record_agent_adds_to_state(self, state_dir: Path) -> None:
        """record_agent adds a running agent to state."""
        save_state(session_id="sess-agent", project_dir=str(state_dir))
        state = record_agent(
            agent_id="agent-01",
            description="Implementing auth module",
            files_expected=["lib/auth.py"],
            project_dir=str(state_dir),
        )
        assert len(state["agents"]) == 1
        agent = state["agents"][0]
        assert agent["id"] == "agent-01"
        assert agent["status"] == "running"
        assert agent["files_expected"] == ["lib/auth.py"]
        assert agent["files_created"] == []

    def test_record_agent_replaces_existing(self, state_dir: Path) -> None:
        """record_agent with same id replaces the previous entry."""
        save_state(session_id="sess-replace", project_dir=str(state_dir))
        record_agent("a1", "first version", project_dir=str(state_dir))
        state = record_agent("a1", "second version", project_dir=str(state_dir))
        assert len(state["agents"]) == 1
        assert state["agents"][0]["description"] == "second version"

    def test_record_multiple_agents(self, state_dir: Path) -> None:
        """Multiple agents can be recorded."""
        save_state(session_id="sess-multi", project_dir=str(state_dir))
        record_agent("a1", "agent one", project_dir=str(state_dir))
        state = record_agent("a2", "agent two", project_dir=str(state_dir))
        assert len(state["agents"]) == 2

    def test_mark_agent_complete_updates_status(self, state_dir: Path) -> None:
        """mark_agent_complete changes status and records files_created."""
        save_state(session_id="sess-complete", project_dir=str(state_dir))
        record_agent("a1", "building feature", files_expected=["out.py"], project_dir=str(state_dir))
        state = mark_agent_complete(
            "a1",
            files_created=["out.py", "test_out.py"],
            status="completed",
            project_dir=str(state_dir),
        )
        agent = state["agents"][0]
        assert agent["status"] == "completed"
        assert agent["files_created"] == ["out.py", "test_out.py"]

    def test_mark_agent_failed(self, state_dir: Path) -> None:
        """mark_agent_complete can set status to 'failed'."""
        save_state(session_id="sess-fail", project_dir=str(state_dir))
        record_agent("a1", "attempt", project_dir=str(state_dir))
        state = mark_agent_complete("a1", status="failed", project_dir=str(state_dir))
        assert state["agents"][0]["status"] == "failed"

    def test_mark_unknown_agent_raises(self, state_dir: Path) -> None:
        """mark_agent_complete raises KeyError for unknown agent_id."""
        save_state(session_id="sess-unknown", project_dir=str(state_dir))
        with pytest.raises(KeyError, match="not found"):
            mark_agent_complete("nonexistent", project_dir=str(state_dir))

    def test_mark_agent_no_state_raises(self, state_dir: Path) -> None:
        """mark_agent_complete raises KeyError when no state file exists."""
        with pytest.raises(KeyError, match="No session state"):
            mark_agent_complete("a1", project_dir=str(state_dir))

    def test_record_agent_without_prior_state(self, state_dir: Path) -> None:
        """record_agent creates a new state if none exists."""
        state = record_agent("a1", "new agent", project_dir=str(state_dir))
        assert len(state["agents"]) == 1
        loaded = load_state(project_dir=str(state_dir))
        assert loaded is not None


# ---------------------------------------------------------------------------
# Pending tasks lifecycle
# ---------------------------------------------------------------------------


class TestPendingTasks:
    """Tests for add_pending_task and complete_pending_task."""

    def test_add_pending_task(self, state_dir: Path) -> None:
        """add_pending_task adds task to pending list."""
        save_state(session_id="sess-tasks", project_dir=str(state_dir))
        state = add_pending_task("implement feature X", project_dir=str(state_dir))
        assert "implement feature X" in state["pending_tasks"]

    def test_add_duplicate_task_is_idempotent(self, state_dir: Path) -> None:
        """Adding the same task twice does not create duplicates."""
        save_state(session_id="sess-dedup", project_dir=str(state_dir))
        add_pending_task("task-a", project_dir=str(state_dir))
        state = add_pending_task("task-a", project_dir=str(state_dir))
        assert state["pending_tasks"].count("task-a") == 1

    def test_complete_pending_task_moves_to_completed(self, state_dir: Path) -> None:
        """complete_pending_task moves task from pending to completed."""
        save_state(session_id="sess-complete-task", project_dir=str(state_dir))
        add_pending_task("task-b", project_dir=str(state_dir))
        state = complete_pending_task("task-b", project_dir=str(state_dir))
        assert "task-b" not in state["pending_tasks"]
        assert "task-b" in state["completed_tasks"]

    def test_complete_unknown_task_raises(self, state_dir: Path) -> None:
        """complete_pending_task raises KeyError for unknown task."""
        save_state(session_id="sess-unknown-task", project_dir=str(state_dir))
        with pytest.raises(KeyError, match="not found"):
            complete_pending_task("nonexistent", project_dir=str(state_dir))

    def test_complete_task_no_state_raises(self, state_dir: Path) -> None:
        """complete_pending_task raises KeyError when no state file exists."""
        with pytest.raises(KeyError, match="No session state"):
            complete_pending_task("task-a", project_dir=str(state_dir))

    def test_complete_task_idempotent_in_completed(self, state_dir: Path) -> None:
        """Completing a task that was re-added does not duplicate in completed."""
        save_state(session_id="sess-idem", project_dir=str(state_dir))
        add_pending_task("task-c", project_dir=str(state_dir))
        complete_pending_task("task-c", project_dir=str(state_dir))
        # Add and complete again
        add_pending_task("task-c", project_dir=str(state_dir))
        state = complete_pending_task("task-c", project_dir=str(state_dir))
        assert state["completed_tasks"].count("task-c") == 1

    def test_add_task_without_prior_state(self, state_dir: Path) -> None:
        """add_pending_task creates a new state if none exists."""
        state = add_pending_task("orphan task", project_dir=str(state_dir))
        assert "orphan task" in state["pending_tasks"]


# ---------------------------------------------------------------------------
# checkpoint
# ---------------------------------------------------------------------------


class TestCheckpoint:
    """Tests for checkpoint function."""

    def test_checkpoint_updates_timestamp(self, state_dir: Path) -> None:
        """checkpoint updates last_checkpoint timestamp."""
        save_state(session_id="sess-ckpt", project_dir=str(state_dir))
        state1 = load_state(project_dir=str(state_dir))
        assert state1 is not None
        ts1 = state1["last_checkpoint"]

        time.sleep(0.01)  # Ensure time advances
        state2 = checkpoint("progress note", project_dir=str(state_dir))
        assert state2["last_checkpoint"] >= ts1
        assert state2["checkpoint_note"] == "progress note"

    def test_checkpoint_preserves_other_fields(self, state_dir: Path) -> None:
        """checkpoint does not alter agents, tasks, or stats."""
        save_state(
            session_id="sess-preserve",
            agents=[{"id": "a1", "description": "x", "status": "running", "files_expected": [], "files_created": []}],
            pending_tasks=["task-1"],
            stats={"key": "val"},
            project_dir=str(state_dir),
        )
        state = checkpoint("check", project_dir=str(state_dir))
        assert len(state["agents"]) == 1
        assert state["pending_tasks"] == ["task-1"]
        assert state["stats"]["key"] == "val"

    def test_checkpoint_without_prior_state(self, state_dir: Path) -> None:
        """checkpoint creates a new state if none exists."""
        state = checkpoint("first checkpoint", project_dir=str(state_dir))
        assert state["checkpoint_note"] == "first checkpoint"
        loaded = load_state(project_dir=str(state_dir))
        assert loaded is not None


# ---------------------------------------------------------------------------
# Atomic write safety
# ---------------------------------------------------------------------------


class TestAtomicWrite:
    """Tests for atomic write preventing corruption."""

    def test_atomic_write_produces_valid_json(self, state_dir: Path) -> None:
        """_atomic_write creates a well-formed JSON file."""
        path = str(state_dir / ".cognitive-os" / "session-state.json")
        data = {"session_id": "test", "key": "value"}
        _atomic_write(path, data)
        with open(path) as f:
            loaded = json.load(f)
        assert loaded == data

    def test_concurrent_writes_produce_valid_json(self, state_dir: Path) -> None:
        """Multiple concurrent writes do not corrupt the file."""
        errors = []

        def writer(n: int) -> None:
            try:
                save_state(
                    session_id=f"sess-{n}",
                    pending_tasks=[f"task-{n}"],
                    checkpoint_note=f"writer {n}",
                    project_dir=str(state_dir),
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent writes produced errors: {errors}"

        # The file must be valid JSON regardless of which writer won
        loaded = load_state(project_dir=str(state_dir))
        assert loaded is not None
        assert "session_id" in loaded

    def test_atomic_write_creates_directories(self, tmp_path: Path) -> None:
        """_atomic_write creates parent directories if needed."""
        deep_path = str(tmp_path / "a" / "b" / "c" / "state.json")
        _atomic_write(deep_path, {"session_id": "deep"})
        with open(deep_path) as f:
            loaded = json.load(f)
        assert loaded["session_id"] == "deep"


# ---------------------------------------------------------------------------
# Cross-session recovery
# ---------------------------------------------------------------------------


class TestCrossSessionRecovery:
    """Tests for state surviving across sessions."""

    def test_state_survives_session_restart(self, state_dir: Path) -> None:
        """State written by session A can be read by session B."""
        # Session A writes state
        save_state(
            session_id="session-A",
            agents=[{"id": "a1", "description": "running task", "status": "running", "files_expected": ["out.py"], "files_created": []}],
            pending_tasks=["finish feature"],
            checkpoint_note="mid-work",
            stats={"commits": 5},
            project_dir=str(state_dir),
        )

        # Session B reads state (simulating a new session)
        recovered = load_state(project_dir=str(state_dir))
        assert recovered is not None
        assert recovered["session_id"] == "session-A"
        assert recovered["checkpoint_note"] == "mid-work"
        assert len(recovered["agents"]) == 1
        assert recovered["agents"][0]["status"] == "running"
        assert recovered["pending_tasks"] == ["finish feature"]
        assert recovered["stats"]["commits"] == 5

    def test_new_session_can_update_old_state(self, state_dir: Path) -> None:
        """A new session can read old state and write updates."""
        # Old session
        save_state(
            session_id="old",
            pending_tasks=["leftover"],
            project_dir=str(state_dir),
        )

        # New session reads and creates fresh state
        old = load_state(project_dir=str(state_dir))
        assert old is not None
        assert old["pending_tasks"] == ["leftover"]

        # New session writes its own state
        save_state(
            session_id="new",
            pending_tasks=["leftover", "new-task"],
            checkpoint_note="continuing from old session",
            project_dir=str(state_dir),
        )
        new_state = load_state(project_dir=str(state_dir))
        assert new_state is not None
        assert new_state["session_id"] == "new"
        assert "leftover" in new_state["pending_tasks"]


# ---------------------------------------------------------------------------
# State path resolution
# ---------------------------------------------------------------------------


class TestStatePath:
    """Tests for _state_path resolution."""

    def test_state_path_uses_project_dir(self, tmp_path: Path) -> None:
        """_state_path uses the provided project_dir."""
        path = _state_path(str(tmp_path))
        assert path == str(tmp_path / ".cognitive-os" / "session-state.json")

    def test_state_path_falls_back_to_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """_state_path uses CLAUDE_PROJECT_DIR when project_dir is None."""
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        path = _state_path(None)
        assert str(tmp_path) in path


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_state_has_required_keys(self) -> None:
        """_empty_state returns a dict with all required keys."""
        state = _empty_state("test-id")
        required_keys = {"session_id", "started_at", "last_checkpoint", "checkpoint_note", "agents", "pending_tasks", "completed_tasks", "stats"}
        assert required_keys.issubset(set(state.keys()))
        assert state["session_id"] == "test-id"

    def test_full_lifecycle(self, state_dir: Path) -> None:
        """End-to-end lifecycle: save, record agents, tasks, checkpoint, complete."""
        # Initialize
        save_state(session_id="lifecycle", project_dir=str(state_dir))

        # Add agents
        record_agent("builder", "Building auth module", ["auth.py"], project_dir=str(state_dir))
        record_agent("tester", "Writing tests", ["test_auth.py"], project_dir=str(state_dir))

        # Add tasks
        add_pending_task("implement login", project_dir=str(state_dir))
        add_pending_task("implement logout", project_dir=str(state_dir))

        # Checkpoint
        checkpoint("agents launched, tasks queued", project_dir=str(state_dir))

        # Complete one agent
        mark_agent_complete("builder", files_created=["auth.py"], project_dir=str(state_dir))

        # Complete one task
        complete_pending_task("implement login", project_dir=str(state_dir))

        # Verify final state
        state = load_state(project_dir=str(state_dir))
        assert state is not None
        assert state["session_id"] == "lifecycle"
        assert len(state["agents"]) == 2

        builder = next(a for a in state["agents"] if a["id"] == "builder")
        tester = next(a for a in state["agents"] if a["id"] == "tester")
        assert builder["status"] == "completed"
        assert tester["status"] == "running"

        assert state["pending_tasks"] == ["implement logout"]
        assert state["completed_tasks"] == ["implement login"]
        assert state["checkpoint_note"] == "agents launched, tasks queued"
