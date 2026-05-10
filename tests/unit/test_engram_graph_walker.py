"""Unit tests for lib.engram_graph_walker — Phase 3 of ADR-071.

All tests use a temporary SQLite database with the memory_relations schema.
No engram daemon or HTTP calls required.
"""

from __future__ import annotations

import sqlite3
import tempfile
import os
from unittest.mock import MagicMock


from lib.engram_graph_walker import EngramGraphWalker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_test_db(path: str) -> sqlite3.Connection:
    """Create a SQLite DB with the engram schema at *path*."""
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_id TEXT UNIQUE,
            title TEXT,
            content TEXT,
            type TEXT,
            topic_key TEXT,
            project TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE memory_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_id TEXT NOT NULL UNIQUE,
            source_id TEXT,
            target_id TEXT,
            relation TEXT NOT NULL DEFAULT 'pending',
            reason TEXT,
            evidence TEXT,
            confidence REAL,
            judgment_status TEXT NOT NULL DEFAULT 'pending',
            superseded_at TEXT,
            superseded_by_relation_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    return conn


def _insert_obs(conn: sqlite3.Connection, sync_id: str, title: str = "T") -> None:
    conn.execute(
        "INSERT INTO observations (sync_id, title, content, type, topic_key, project, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (sync_id, title, "content", "decision", "test/key", "proj", "2026-04-27T10:00:00Z"),
    )
    conn.commit()


def _insert_relation(
    conn: sqlite3.Connection,
    rel_sync_id: str,
    source_id: str,
    target_id: str,
    relation: str = "related",
    judgment_status: str = "approved",
) -> None:
    conn.execute(
        "INSERT INTO memory_relations (sync_id, source_id, target_id, relation, judgment_status) "
        "VALUES (?, ?, ?, ?, ?)",
        (rel_sync_id, source_id, target_id, relation, judgment_status),
    )
    conn.commit()


def _walker(db_path: str) -> EngramGraphWalker:
    http_mock = MagicMock()
    http_mock.is_available.return_value = True
    return EngramGraphWalker(db_path=db_path, http_client_module=http_mock)


# ---------------------------------------------------------------------------
# walk() — BFS traversal
# ---------------------------------------------------------------------------


class TestWalk:
    def test_empty_db_returns_empty(self):
        """No relations → walk returns empty dict."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            conn.close()
            w = _walker(path)
            result = w.walk(["obs-A"])
            assert result == {}
        finally:
            os.unlink(path)

    def test_nonexistent_db_returns_empty(self):
        """Missing DB file → walk returns empty dict gracefully."""
        w = EngramGraphWalker(db_path="/tmp/does-not-exist-99999.db")
        result = w.walk(["obs-A"])
        assert result == {}

    def test_direct_neighbor_found(self):
        """A → B: walk([A]) returns {B: hops=1}."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            _insert_obs(conn, "obs-A")
            _insert_obs(conn, "obs-B")
            _insert_relation(conn, "rel-1", "obs-A", "obs-B")
            conn.close()

            w = _walker(path)
            result = w.walk(["obs-A"])
            assert "obs-B" in result
            assert result["obs-B"]["hops"] == 1
        finally:
            os.unlink(path)

    def test_two_hop_neighbor_found(self):
        """A → B → C: walk([A], max_depth=2) returns both B and C."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            for sid in ("obs-A", "obs-B", "obs-C"):
                _insert_obs(conn, sid)
            _insert_relation(conn, "rel-1", "obs-A", "obs-B")
            _insert_relation(conn, "rel-2", "obs-B", "obs-C")
            conn.close()

            w = _walker(path)
            result = w.walk(["obs-A"], max_depth=2)
            assert "obs-B" in result
            assert "obs-C" in result
            assert result["obs-B"]["hops"] == 1
            assert result["obs-C"]["hops"] == 2
        finally:
            os.unlink(path)

    def test_depth_limit_respected(self):
        """A → B → C → D: walk([A], max_depth=2) returns B and C but NOT D."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            for sid in ("obs-A", "obs-B", "obs-C", "obs-D"):
                _insert_obs(conn, sid)
            _insert_relation(conn, "rel-1", "obs-A", "obs-B")
            _insert_relation(conn, "rel-2", "obs-B", "obs-C")
            _insert_relation(conn, "rel-3", "obs-C", "obs-D")
            conn.close()

            w = _walker(path)
            result = w.walk(["obs-A"], max_depth=2)
            assert "obs-B" in result
            assert "obs-C" in result
            assert "obs-D" not in result
        finally:
            os.unlink(path)

    def test_rejected_relation_skipped(self):
        """Relations with judgment_status='rejected' are excluded."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            _insert_obs(conn, "obs-A")
            _insert_obs(conn, "obs-B")
            _insert_relation(conn, "rel-1", "obs-A", "obs-B", judgment_status="rejected")
            conn.close()

            w = _walker(path)
            result = w.walk(["obs-A"])
            assert "obs-B" not in result
        finally:
            os.unlink(path)

    def test_starting_ids_excluded_from_result(self):
        """Start nodes never appear in the returned neighbor dict."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            _insert_obs(conn, "obs-A")
            _insert_obs(conn, "obs-B")
            _insert_relation(conn, "rel-1", "obs-A", "obs-B")
            conn.close()

            w = _walker(path)
            result = w.walk(["obs-A"])
            assert "obs-A" not in result
        finally:
            os.unlink(path)

    def test_bidirectional_deduplication(self):
        """Bidirectional edges (A→B and B→A) don't create cycles or duplicates."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            _insert_obs(conn, "obs-A")
            _insert_obs(conn, "obs-B")
            _insert_relation(conn, "rel-1", "obs-A", "obs-B")
            _insert_relation(conn, "rel-2", "obs-B", "obs-A")
            conn.close()

            w = _walker(path)
            result = w.walk(["obs-A"])
            assert "obs-B" in result
            assert result["obs-B"]["hops"] == 1
        finally:
            os.unlink(path)

    def test_empty_sync_ids_returns_empty(self):
        w = EngramGraphWalker(db_path="/tmp/nonexistent.db")
        result = w.walk([])
        assert result == {}


# ---------------------------------------------------------------------------
# merge_into_results()
# ---------------------------------------------------------------------------


class TestMergeIntoResults:
    def _make_obs_dict(self, sync_id: str, score: float = 1.0) -> dict:
        return {
            "id": 1,
            "sync_id": sync_id,
            "title": "T",
            "content": "C",
            "adjusted_score": score,
        }

    def test_empty_neighbors_preserves_base_order(self):
        base = [
            self._make_obs_dict("obs-A", score=0.9),
            self._make_obs_dict("obs-B", score=0.7),
        ]
        w = EngramGraphWalker(db_path="/tmp/nonexistent.db")
        result = w.merge_into_results(base, {})
        assert [r["sync_id"] for r in result] == ["obs-A", "obs-B"]

    def test_graph_only_neighbor_added_to_result(self):
        """A graph-only neighbor is appended with graph_boost score."""
        base = [self._make_obs_dict("obs-A", score=0.9)]
        neighbors = {"obs-B": {"hops": 1, "relation_path": ["related"]}}

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            _insert_obs(conn, "obs-B", title="Neighbor B")
            conn.close()

            w = _walker(path)
            result = w.merge_into_results(base, neighbors)
            sync_ids = [r["sync_id"] for r in result]
            assert "obs-A" in sync_ids
            assert "obs-B" in sync_ids
        finally:
            os.unlink(path)

    def test_graph_only_neighbor_preserves_wave2_schema_columns_when_present(self):
        base = [self._make_obs_dict("obs-A", score=0.9)]
        neighbors = {"obs-B": {"hops": 1, "relation_path": ["related"]}}

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            conn.execute("ALTER TABLE observations ADD COLUMN valid_from TEXT")
            conn.execute("ALTER TABLE observations ADD COLUMN valid_to TEXT")
            conn.execute("ALTER TABLE observations ADD COLUMN memory_class TEXT")
            conn.execute("ALTER TABLE observations ADD COLUMN source_episode TEXT")
            _insert_obs(conn, "obs-B", title="Neighbor B")
            conn.execute(
                """
                UPDATE observations
                SET valid_from = ?, valid_to = ?, memory_class = ?, source_episode = ?
                WHERE sync_id = ?
                """,
                (
                    "2026-04-27T10:00:00Z",
                    None,
                    "semantic",
                    "session-1",
                    "obs-B",
                ),
            )
            conn.commit()
            conn.close()

            result = _walker(path).merge_into_results(base, neighbors)
            neighbor = next(row for row in result if row["sync_id"] == "obs-B")
            assert neighbor["valid_from"] == "2026-04-27T10:00:00Z"
            assert neighbor["valid_to"] is None
            assert neighbor["memory_class"] == "semantic"
            assert neighbor["source_episode"] == "session-1"
        finally:
            os.unlink(path)

    def test_final_score_formula_applied(self):
        """Base score is multiplied by (1 - alpha_graph) in the final_score."""
        base = [self._make_obs_dict("obs-A", score=1.0)]
        w = EngramGraphWalker(db_path="/tmp/nonexistent.db")
        result = w.merge_into_results(base, {}, alpha_graph=0.2, graph_boost=0.3)
        assert len(result) == 1
        expected_final = 1.0 * (1.0 - 0.2) + 0.3 * 0.2
        assert abs(result[0]["final_score"] - expected_final) < 1e-9

    def test_result_sorted_descending_by_final_score(self):
        """Result is sorted by final_score descending."""
        base = [
            self._make_obs_dict("obs-low", score=0.2),
            self._make_obs_dict("obs-high", score=0.9),
        ]
        w = EngramGraphWalker(db_path="/tmp/nonexistent.db")
        result = w.merge_into_results(base, {})
        assert result[0]["sync_id"] == "obs-high"
        assert result[1]["sync_id"] == "obs-low"


class TestTemporalStatus:
    def test_supersedes_relation_marks_source_current_and_target_stale(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            _insert_obs(conn, "obs-current")
            _insert_obs(conn, "obs-stale")
            _insert_relation(
                conn,
                "rel-1",
                "obs-current",
                "obs-stale",
                relation="supersedes",
            )
            conn.close()

            result = _walker(path).temporal_status(["obs-current", "obs-stale"])

            assert result["obs-current"]["is_current"] is True
            assert result["obs-current"]["supersedes"] == ["obs-stale"]
            assert result["obs-stale"]["is_superseded"] is True
            assert result["obs-stale"]["superseded_by"] == ["obs-current"]
        finally:
            os.unlink(path)

    def test_rejected_supersedes_relation_does_not_mark_temporal_status(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            _insert_obs(conn, "obs-current")
            _insert_obs(conn, "obs-stale")
            _insert_relation(
                conn,
                "rel-1",
                "obs-current",
                "obs-stale",
                relation="supersedes",
                judgment_status="rejected",
            )
            conn.close()

            result = _walker(path).temporal_status(["obs-current", "obs-stale"])

            assert result["obs-current"]["is_current"] is False
            assert result["obs-stale"]["is_superseded"] is False
        finally:
            os.unlink(path)


class TestSupportChains:
    def test_support_chain_finds_two_hop_relation_path(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            for sid in ("obs-query", "obs-impl", "obs-test"):
                _insert_obs(conn, sid)
            _insert_relation(conn, "rel-1", "obs-query", "obs-impl", relation="implemented_by")
            _insert_relation(conn, "rel-2", "obs-impl", "obs-test", relation="verified_by")
            conn.close()

            result = _walker(path).support_chains(["obs-query"], ["obs-test"], max_depth=2)

            assert result["obs-test"] == ["obs-query", "obs-impl", "obs-test"]
        finally:
            os.unlink(path)


class TestPersonalizedPageRank:
    def test_ppr_scores_connected_candidate_above_unconnected_candidate(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            for sid in ("obs-query", "obs-impl", "obs-test", "obs-other"):
                _insert_obs(conn, sid)
            _insert_relation(conn, "rel-1", "obs-query", "obs-impl", relation="implemented_by")
            _insert_relation(conn, "rel-2", "obs-impl", "obs-test", relation="verified_by")
            conn.close()

            result = _walker(path).personalized_pagerank(
                ["obs-query"],
                ["obs-test", "obs-other"],
                iterations=10,
            )

            assert result["obs-test"] > result["obs-other"]
        finally:
            os.unlink(path)

    def test_support_chain_respects_depth_limit(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            conn = _create_test_db(path)
            for sid in ("obs-query", "obs-impl", "obs-test"):
                _insert_obs(conn, sid)
            _insert_relation(conn, "rel-1", "obs-query", "obs-impl", relation="implemented_by")
            _insert_relation(conn, "rel-2", "obs-impl", "obs-test", relation="verified_by")
            conn.close()

            result = _walker(path).support_chains(["obs-query"], ["obs-test"], max_depth=1)

            assert result == {}
        finally:
            os.unlink(path)
