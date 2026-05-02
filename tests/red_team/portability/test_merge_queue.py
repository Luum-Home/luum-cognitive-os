"""
Portability proofs for lib/merge_queue — P2.2 (ADR-116).

3 proofs:
1. Works with an arbitrary MERGE_QUEUE_PATH env var (no .cognitive-os dir needed).
2. Queue is valid JSONL: every persisted line is independently parseable.
3. Cross-process enqueue produces entries readable by a fresh process import.
"""

from __future__ import annotations

import json
import multiprocessing
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Proof 1: arbitrary MERGE_QUEUE_PATH (no .cognitive-os anchor needed)
# ---------------------------------------------------------------------------


class TestArbitraryQueuePath:
    """merge_queue works with any writable directory — no special anchor."""

    def test_env_var_path(self, tmp_path, monkeypatch):
        custom_path = tmp_path / "custom" / "q.jsonl"
        monkeypatch.setenv("MERGE_QUEUE_PATH", str(custom_path))

        # Resolve through MERGE_QUEUE_PATH without requiring a .cognitive-os anchor.
        import lib.merge_queue as mq  # noqa: PLC0415

        eid = mq.enqueue("session/env", "test-env")
        assert custom_path.exists(), "queue file should be created automatically"
        entry = mq.status(eid)
        assert entry is not None
        assert entry["session_branch"] == "session/env"

    def test_explicit_path_overrides_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MERGE_QUEUE_PATH", str(tmp_path / "env-q.jsonl"))
        explicit = tmp_path / "explicit-q.jsonl"

        from lib.merge_queue import enqueue  # noqa: PLC0415

        enqueue("session/explicit", "test-explicit", queue_path=explicit)
        assert explicit.exists()
        # The env-var file should NOT have been written.
        assert not (tmp_path / "env-q.jsonl").exists()


# ---------------------------------------------------------------------------
# Proof 2: every line in the JSONL is independently valid JSON
# ---------------------------------------------------------------------------


class TestJsonlIntegrity:
    """The queue file is valid JSONL: each line parses independently."""

    def test_each_line_is_valid_json(self, tmp_path):
        queue_file = tmp_path / "q.jsonl"
        from lib.merge_queue import enqueue  # noqa: PLC0415

        branches = [f"session/branch-{i}" for i in range(5)]
        for b in branches:
            enqueue(b, "test-jsonl", queue_path=queue_file)

        lines = [l for l in queue_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 5
        for line in lines:
            obj = json.loads(line)  # must not raise
            assert "id" in obj
            assert "session_branch" in obj
            assert "status" in obj

    def test_schema_fields_present(self, tmp_path):
        queue_file = tmp_path / "q.jsonl"
        from lib.merge_queue import enqueue  # noqa: PLC0415

        required_fields = {
            "id", "session_branch", "session_id", "expected_files",
            "enqueued_at", "status", "completed_at", "notes",
        }
        enqueue("session/schema", "test-schema", expected_files=["a.py"], queue_path=queue_file)
        line = queue_file.read_text().strip()
        obj = json.loads(line)
        missing = required_fields - obj.keys()
        assert not missing, f"Schema fields missing: {missing}"


# ---------------------------------------------------------------------------
# Proof 3: cross-process enqueue readable by fresh import
# ---------------------------------------------------------------------------


class TestCrossProcessReadability:
    """Entry written by a child process is readable by the parent's fresh import."""

    @staticmethod
    def _child_enqueue(queue_file: str, result_q):
        """Run in a subprocess: enqueue one entry and return its id."""
        sys.path.insert(0, str(REPO_ROOT))
        from lib.merge_queue import enqueue  # noqa: PLC0415

        eid = enqueue("session/cross-proc", "child-session", queue_path=Path(queue_file))
        result_q.put(eid)

    def test_entry_visible_to_parent(self, tmp_path):
        queue_file = tmp_path / "q.jsonl"
        result_q: multiprocessing.Queue = multiprocessing.Queue()

        p = multiprocessing.Process(
            target=self._child_enqueue,
            args=(str(queue_file), result_q),
        )
        p.start()
        p.join(timeout=10)
        assert p.exitcode == 0

        child_id = result_q.get_nowait()

        # Parent reads the entry using its own import (no shared state).
        from lib.merge_queue import status  # noqa: PLC0415

        entry = status(child_id, queue_path=queue_file)
        assert entry is not None, "Parent could not read entry written by child"
        assert entry["id"] == child_id
        assert entry["session_branch"] == "session/cross-proc"
