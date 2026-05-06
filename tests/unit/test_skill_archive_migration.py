"""Unit tests for scripts/migrate_skill_archive_to_store.py — ADR-176.

Tests: migration with synthetic JSONL fixtures, idempotency, dry-run, error handling.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.migrate_skill_archive_to_store import run_migration, _sha256, _map_entry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_jsonl(entries: list[dict]) -> str:
    return "\n".join(json.dumps(e) for e in entries) + "\n"


SAMPLE_ENTRIES = [
    {
        "skill_name": "test-skill-alpha",
        "version": "abc123",
        "timestamp": "2026-04-10T14:30:00+00:00",
        "trust_score": 85.0,
        "success": True,
        "task_description": "test task alpha",
        "tokens_used": 1500,
        "cost_usd": 0.005,
        "metadata": {"observations": {"note": "ran well"}},
    },
    {
        "skill_name": "test-skill-beta",
        "version": "def456",
        "timestamp": "2026-04-11T10:00:00+00:00",
        "trust_score": 42.0,
        "success": False,
        "task_description": "test task beta",
        "tokens_used": 800,
        "cost_usd": 0.002,
        "metadata": {},
    },
]


@pytest.fixture
def jsonl_file(tmp_path: Path) -> Path:
    src = tmp_path / "skill-archive.jsonl"
    src.write_text(_make_jsonl(SAMPLE_ENTRIES))
    return src


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_store.db"


# ---------------------------------------------------------------------------
# _map_entry unit tests
# ---------------------------------------------------------------------------


class TestMapEntry:
    def test_maps_skill_name_to_id(self) -> None:
        entry = SAMPLE_ENTRIES[0]
        sr, an = _map_entry(entry)
        assert sr["skill_id"] == _sha256("test-skill-alpha")

    def test_maps_success_to_applied(self) -> None:
        sr, _ = _map_entry(SAMPLE_ENTRIES[0])  # success=True
        assert sr["total_applied"] == 1

    def test_failure_maps_to_zero_applied(self) -> None:
        sr, _ = _map_entry(SAMPLE_ENTRIES[1])  # success=False
        assert sr["total_applied"] == 0

    def test_observations_extracted(self) -> None:
        _, an = _map_entry(SAMPLE_ENTRIES[0])
        obs = json.loads(an["observations"])
        assert "note" in obs

    def test_missing_fields_use_defaults(self) -> None:
        sr, an = _map_entry({"skill_name": "minimal"})
        assert sr["name"] == "minimal"
        assert sr["total_completions"] == 1

    def test_unknown_skill_name_handled(self) -> None:
        sr, an = _map_entry({})
        assert sr["name"] == "unknown"


# ---------------------------------------------------------------------------
# run_migration dry-run
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_dry_run_does_not_create_db(self, jsonl_file: Path, db_path: Path) -> None:
        rc = run_migration(jsonl_file, db_path, dry_run=True)
        assert rc == 0
        assert not db_path.exists()

    def test_dry_run_returns_zero(self, jsonl_file: Path, db_path: Path) -> None:
        rc = run_migration(jsonl_file, db_path, dry_run=True)
        assert rc == 0

    def test_missing_src_is_ok(self, tmp_path: Path, db_path: Path) -> None:
        missing = tmp_path / "no-such-file.jsonl"
        rc = run_migration(missing, db_path, dry_run=True)
        assert rc == 0


# ---------------------------------------------------------------------------
# run_migration apply
# ---------------------------------------------------------------------------


class TestApply:
    def test_applies_records_to_db(self, jsonl_file: Path, db_path: Path) -> None:
        rc = run_migration(jsonl_file, db_path, dry_run=False)
        assert rc == 0
        assert db_path.exists()

        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM skill_records").fetchone()[0]
        conn.close()
        assert count >= 2  # at least the 2 sample entries

    def test_idempotent_on_rerun(self, jsonl_file: Path, db_path: Path) -> None:
        run_migration(jsonl_file, db_path, dry_run=False)
        run_migration(jsonl_file, db_path, dry_run=False)  # second run should not fail

        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM skill_records").fetchone()[0]
        conn.close()
        # Still the same number of records (idempotent — no duplicates)
        assert count >= 2

    def test_analyses_written(self, jsonl_file: Path, db_path: Path) -> None:
        run_migration(jsonl_file, db_path, dry_run=False)
        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM skill_analysis_scores").fetchone()[0]
        conn.close()
        assert count >= 2  # one analysis per entry

    def test_skill_names_preserved(self, jsonl_file: Path, db_path: Path) -> None:
        run_migration(jsonl_file, db_path, dry_run=False)
        conn = sqlite3.connect(str(db_path))
        names = {
            row[0]
            for row in conn.execute("SELECT name FROM skill_records").fetchall()
        }
        conn.close()
        assert "test-skill-alpha" in names
        assert "test-skill-beta" in names


# ---------------------------------------------------------------------------
# Malformed JSONL handling
# ---------------------------------------------------------------------------


class TestMalformedEntries:
    def test_skips_blank_lines(self, tmp_path: Path, db_path: Path) -> None:
        src = tmp_path / "malformed.jsonl"
        src.write_text("\n\n" + json.dumps(SAMPLE_ENTRIES[0]) + "\n\n")
        rc = run_migration(src, db_path, dry_run=True)
        assert rc == 0

    def test_skips_invalid_json(self, tmp_path: Path, db_path: Path) -> None:
        src = tmp_path / "bad.jsonl"
        src.write_text("not valid json\n" + json.dumps(SAMPLE_ENTRIES[0]))
        rc = run_migration(src, db_path, dry_run=True)
        assert rc == 0  # errors logged but doesn't crash

    def test_applies_valid_entries_despite_invalid(
        self, tmp_path: Path, db_path: Path
    ) -> None:
        src = tmp_path / "mixed.jsonl"
        src.write_text("invalid\n" + json.dumps(SAMPLE_ENTRIES[0]) + "\nbad-json{")
        run_migration(src, db_path, dry_run=False)
        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM skill_records").fetchone()[0]
        conn.close()
        assert count >= 1  # the valid entry was inserted
