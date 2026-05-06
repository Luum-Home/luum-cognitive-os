"""Unit tests for lib/skill_store.py — ADR-176.

Tests: schema creation, all 7 record_* methods, query_lineage, query_recent.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from lib.skill_store import SkillStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_store(tmp_path: Path) -> SkillStore:
    store = SkillStore(tmp_path / "test_skill_store.db")
    yield store
    store.close()


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------


class TestSchemaCreation:
    def test_six_core_tables_exist(self, tmp_store: SkillStore) -> None:
        """DB initialises with all 6 OpenSpace tables + 1 COS extension."""
        conn = sqlite3.connect(str(tmp_store._db_path))
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()

        expected = {
            "skill_records",
            "skill_lineage_parents",
            "execution_analyses",
            "skill_judgments",
            "skill_tool_deps",
            "skill_tags",
            # COS extension
            "skill_analysis_scores",
        }
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"

    def test_indexes_exist(self, tmp_store: SkillStore) -> None:
        conn = sqlite3.connect(str(tmp_store._db_path))
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        conn.close()
        assert "idx_sr_name" in indexes
        assert "idx_ea_task" in indexes
        assert "idx_lp_parent" in indexes

    def test_wal_mode(self, tmp_store: SkillStore) -> None:
        result = tmp_store._conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0] == "wal"


# ---------------------------------------------------------------------------
# record_execution
# ---------------------------------------------------------------------------


class TestRecordExecution:
    def test_inserts_skill_record(self, tmp_store: SkillStore) -> None:
        skill_id = tmp_store.record_execution(
            skill_name="test-skill",
            agent_session_id="sess-001",
            tool_count=5,
            duration_ms=1200,
            status="success",
        )
        assert skill_id == _sha("test-skill")

        conn = sqlite3.connect(str(tmp_store._db_path))
        row = conn.execute(
            "SELECT name, total_completions, total_applied FROM skill_records WHERE skill_id=?",
            (skill_id,),
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "test-skill"
        assert row[1] == 1  # total_completions
        assert row[2] == 1  # total_applied (success)

    def test_upserts_on_duplicate(self, tmp_store: SkillStore) -> None:
        for _ in range(3):
            tmp_store.record_execution(
                skill_name="repeated-skill",
                agent_session_id="sess-001",
                tool_count=1,
                duration_ms=100,
                status="success",
            )
        conn = sqlite3.connect(str(tmp_store._db_path))
        row = conn.execute(
            "SELECT total_completions FROM skill_records WHERE skill_id=?",
            (_sha("repeated-skill"),),
        ).fetchone()
        conn.close()
        assert row[0] == 3  # 3 completions, not 1

    def test_failure_status_not_counted_as_applied(self, tmp_store: SkillStore) -> None:
        tmp_store.record_execution(
            skill_name="failing-skill",
            agent_session_id="sess-x",
            tool_count=0,
            duration_ms=0,
            status="error",
        )
        conn = sqlite3.connect(str(tmp_store._db_path))
        row = conn.execute(
            "SELECT total_applied FROM skill_records WHERE skill_id=?",
            (_sha("failing-skill"),),
        ).fetchone()
        conn.close()
        assert row[0] == 0

    def test_output_hash(self, tmp_store: SkillStore) -> None:
        out_hash = SkillStore.hash_output("some output")
        assert len(out_hash) == 64  # SHA-256 hex
        skill_id = tmp_store.record_execution(
            skill_name="hashed-skill",
            agent_session_id="s",
            tool_count=1,
            duration_ms=100,
            status="success",
            output_hash=out_hash,
        )
        conn = sqlite3.connect(str(tmp_store._db_path))
        row = conn.execute(
            "SELECT lineage_content_snapshot FROM skill_records WHERE skill_id=?",
            (skill_id,),
        ).fetchone()
        conn.close()
        snapshot = json.loads(row[0])
        assert snapshot["output_hash"] == out_hash


# ---------------------------------------------------------------------------
# record_lineage
# ---------------------------------------------------------------------------


class TestRecordLineage:
    def test_inserts_lineage_edge(self, tmp_store: SkillStore) -> None:
        # Ensure parent skill record exists
        tmp_store.record_execution("parent-skill", "s", 0, 0, "success")
        tmp_store.record_execution("child-skill", "s", 0, 0, "success")

        child_id = _sha("child-skill")
        parent_id = _sha("parent-skill")
        tmp_store.record_lineage(child_id, parent_id, "derived")

        conn = sqlite3.connect(str(tmp_store._db_path))
        row = conn.execute(
            "SELECT COUNT(*) FROM skill_lineage_parents WHERE skill_id=? AND parent_skill_id=?",
            (child_id, parent_id),
        ).fetchone()
        conn.close()
        assert row[0] == 1

    def test_idempotent_on_duplicate(self, tmp_store: SkillStore) -> None:
        tmp_store.record_execution("p", "s", 0, 0, "success")
        tmp_store.record_execution("c", "s", 0, 0, "success")
        pid, cid = _sha("p"), _sha("c")
        tmp_store.record_lineage(cid, pid)
        tmp_store.record_lineage(cid, pid)  # should not raise

        conn = sqlite3.connect(str(tmp_store._db_path))
        count = conn.execute(
            "SELECT COUNT(*) FROM skill_lineage_parents WHERE skill_id=?", (cid,)
        ).fetchone()[0]
        conn.close()
        assert count == 1


# ---------------------------------------------------------------------------
# record_analysis
# ---------------------------------------------------------------------------


class TestRecordAnalysis:
    def test_inserts_analysis_score(self, tmp_store: SkillStore) -> None:
        tmp_store.record_execution("anal-skill", "s", 0, 0, "success")
        row_id = tmp_store.record_analysis(
            skill_id=_sha("anal-skill"),
            analyzer="test-analyzer",
            score=87.5,
            observations_json='{"note": "good"}',
        )
        assert row_id is not None

        conn = sqlite3.connect(str(tmp_store._db_path))
        row = conn.execute(
            "SELECT analyzer, score FROM skill_analysis_scores WHERE id=?", (row_id,)
        ).fetchone()
        conn.close()
        assert row[0] == "test-analyzer"
        assert row[1] == pytest.approx(87.5)


# ---------------------------------------------------------------------------
# record_judgment
# ---------------------------------------------------------------------------


class TestRecordJudgment:
    def test_inserts_judgment(self, tmp_store: SkillStore) -> None:
        tmp_store.record_execution("judged-skill", "s", 0, 0, "success")
        tmp_store.record_judgment(
            skill_id=_sha("judged-skill"),
            judge_model="claude-opus",
            verdict="approve",
            confidence=0.92,
            rationale="Skill performs well",
        )

        conn = sqlite3.connect(str(tmp_store._db_path))
        row = conn.execute(
            "SELECT skill_applied, note FROM skill_judgments WHERE skill_id=?",
            (_sha("judged-skill"),),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 1  # approve → skill_applied=1
        note = json.loads(row[1])
        assert note["verdict"] == "approve"
        assert note["confidence"] == pytest.approx(0.92)

    def test_reject_verdict_maps_to_not_applied(self, tmp_store: SkillStore) -> None:
        tmp_store.record_execution("rejected-skill", "s", 0, 0, "success")
        tmp_store.record_judgment(
            skill_id=_sha("rejected-skill"),
            judge_model="claude-sonnet",
            verdict="reject",
            confidence=0.80,
            rationale="Needs improvement",
        )
        conn = sqlite3.connect(str(tmp_store._db_path))
        row = conn.execute(
            "SELECT skill_applied FROM skill_judgments WHERE skill_id=?",
            (_sha("rejected-skill"),),
        ).fetchone()
        conn.close()
        assert row[0] == 0


# ---------------------------------------------------------------------------
# record_tool_dep
# ---------------------------------------------------------------------------


class TestRecordToolDep:
    def test_inserts_tool_dep(self, tmp_store: SkillStore) -> None:
        tmp_store.record_execution("dep-skill", "s", 0, 0, "success")
        tmp_store.record_tool_dep(_sha("dep-skill"), "Bash", frequency=2)

        conn = sqlite3.connect(str(tmp_store._db_path))
        row = conn.execute(
            "SELECT tool_key, critical FROM skill_tool_deps WHERE skill_id=?",
            (_sha("dep-skill"),),
        ).fetchone()
        conn.close()
        assert row[0] == "Bash"
        assert row[1] == 0  # frequency=2 < 3

    def test_high_frequency_marks_critical(self, tmp_store: SkillStore) -> None:
        tmp_store.record_execution("critical-skill", "s", 0, 0, "success")
        tmp_store.record_tool_dep(_sha("critical-skill"), "Read", frequency=5)

        conn = sqlite3.connect(str(tmp_store._db_path))
        row = conn.execute(
            "SELECT critical FROM skill_tool_deps WHERE skill_id=?",
            (_sha("critical-skill"),),
        ).fetchone()
        conn.close()
        assert row[0] == 1


# ---------------------------------------------------------------------------
# record_tag
# ---------------------------------------------------------------------------


class TestRecordTag:
    def test_inserts_tag(self, tmp_store: SkillStore) -> None:
        tmp_store.record_execution("tagged-skill", "s", 0, 0, "success")
        tmp_store.record_tag(_sha("tagged-skill"), "sdd", source="auto")

        conn = sqlite3.connect(str(tmp_store._db_path))
        row = conn.execute(
            "SELECT tag FROM skill_tags WHERE skill_id=?",
            (_sha("tagged-skill"),),
        ).fetchone()
        conn.close()
        assert row is not None
        assert "sdd" in row[0]

    def test_custom_source_appended(self, tmp_store: SkillStore) -> None:
        tmp_store.record_execution("src-skill", "s", 0, 0, "success")
        tmp_store.record_tag(_sha("src-skill"), "core", source="manual")

        conn = sqlite3.connect(str(tmp_store._db_path))
        row = conn.execute(
            "SELECT tag FROM skill_tags WHERE skill_id=?",
            (_sha("src-skill"),),
        ).fetchone()
        conn.close()
        assert row[0] == "core:manual"

    def test_idempotent(self, tmp_store: SkillStore) -> None:
        tmp_store.record_execution("idem-skill", "s", 0, 0, "success")
        tmp_store.record_tag(_sha("idem-skill"), "workflow")
        tmp_store.record_tag(_sha("idem-skill"), "workflow")  # no error


# ---------------------------------------------------------------------------
# query_lineage
# ---------------------------------------------------------------------------


class TestQueryLineage:
    def _build_chain(self, store: SkillStore, names: list[str]) -> list[str]:
        """Insert a linear lineage chain A → B → C..."""
        ids = []
        for name in names:
            store.record_execution(name, "s", 0, 0, "success")
            ids.append(_sha(name))
        for i in range(1, len(ids)):
            store.record_lineage(ids[i], ids[i - 1])
        return ids

    def test_direct_parent(self, tmp_store: SkillStore) -> None:
        ids = self._build_chain(tmp_store, ["root", "child"])
        lineage = tmp_store.query_lineage(ids[1], depth=1)
        assert len(lineage) == 1
        assert lineage[0] == (ids[0], 1)

    def test_depth_limit(self, tmp_store: SkillStore) -> None:
        # A → B → C → D  (A is root)
        ids = self._build_chain(tmp_store, ["A", "B", "C", "D"])
        # Query from D with depth=2 → should see C (depth 1) and B (depth 2), not A
        lineage = tmp_store.query_lineage(ids[3], depth=2)
        depths = {depth for (_, depth) in lineage}
        assert max(depths) <= 2

    def test_no_lineage_returns_empty(self, tmp_store: SkillStore) -> None:
        tmp_store.record_execution("orphan-skill", "s", 0, 0, "success")
        lineage = tmp_store.query_lineage(_sha("orphan-skill"), depth=3)
        assert lineage == []

    def test_depth_3_traversal(self, tmp_store: SkillStore) -> None:
        # A → B → C → D (4 nodes)
        ids = self._build_chain(tmp_store, ["d-A", "d-B", "d-C", "d-D"])
        lineage = tmp_store.query_lineage(ids[3], depth=3)
        # Should return d-C (depth 1), d-B (depth 2), d-A (depth 3)
        ancestor_ids = {sid for (sid, _) in lineage}
        assert ids[2] in ancestor_ids  # d-C
        assert ids[1] in ancestor_ids  # d-B
        assert ids[0] in ancestor_ids  # d-A


# ---------------------------------------------------------------------------
# query_recent
# ---------------------------------------------------------------------------


class TestQueryRecent:
    def test_returns_recent_executions(self, tmp_store: SkillStore) -> None:
        for _ in range(5):
            tmp_store.record_execution("query-skill", "s", 1, 100, "success")
        results = tmp_store.query_recent("query-skill", limit=10)
        assert len(results) >= 1
        assert results[0]["name"] == "query-skill"

    def test_unknown_skill_returns_empty(self, tmp_store: SkillStore) -> None:
        results = tmp_store.query_recent("no-such-skill", limit=10)
        assert results == []

    def test_result_has_required_keys(self, tmp_store: SkillStore) -> None:
        tmp_store.record_execution("keyed-skill", "s", 0, 0, "success")
        results = tmp_store.query_recent("keyed-skill")
        assert results
        required_keys = {"skill_id", "name", "last_updated", "total_completions", "total_applied"}
        assert required_keys.issubset(results[0].keys())
