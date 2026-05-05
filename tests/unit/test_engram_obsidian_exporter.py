from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from lib.engram_lifecycle import EngramLifecycle
from lib.engram_obsidian_exporter import EngramObsidianExporter

pytestmark = pytest.mark.unit


class FakeHTTP:
    def __init__(self, observations: list[dict[str, Any]]) -> None:
        self.observations = observations

    def get_recent(self, *, limit: int = 100, project: str = "", **_kwargs: Any) -> list[dict[str, Any]]:
        rows = self.observations
        if project:
            rows = [obs for obs in rows if obs.get("project") == project]
        return rows[:limit]


def _obs(
    obs_id: int,
    sync_id: str,
    title: str,
    *,
    topic_key: str = "architecture/memory-lifecycle",
    project: str = "luum-agent-os",
    content: str = "Body",
    created_at: str = "2026-05-05T10:00:00Z",
) -> dict[str, Any]:
    return {
        "id": obs_id,
        "sync_id": sync_id,
        "title": title,
        "content": content,
        "type": "decision",
        "topic_key": topic_key,
        "project": project,
        "created_at": created_at,
        "updated_at": created_at,
    }


def _db_with_relation(path: Path, *, rejected: bool = False) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
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
        """
    )
    conn.execute(
        """
        INSERT INTO memory_relations
            (sync_id, source_id, target_id, relation, confidence, judgment_status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("rel-1", "obs-a", "obs-b", "related", 0.9, "rejected" if rejected else "accepted"),
    )
    conn.commit()
    conn.close()


def _exporter(tmp_path: Path, observations: list[dict[str, Any]], *, rejected: bool = False) -> EngramObsidianExporter:
    db = tmp_path / "engram.db"
    _db_with_relation(db, rejected=rejected)
    return EngramObsidianExporter(
        http_client_module=FakeHTTP(observations),
        db_path=str(db),
        now=lambda: datetime(2026, 5, 5, 12, 0, 0),
    )


def test_dry_run_is_default_and_does_not_create_output_dir(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    observations = [_obs(1, "obs-a", "Alpha")]
    exporter = _exporter(tmp_path, observations)

    result = exporter.export(vault=vault, project="luum-agent-os")

    assert result.dry_run is True
    assert result.files_planned == 1
    assert result.files_written == 0
    assert not (vault / "Cognitive OS").exists()


def test_write_exports_markdown_with_lifecycle_frontmatter(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    lifecycle = EngramLifecycle(now=lambda: datetime(2026, 5, 5, 10, 0, 0))
    content = lifecycle.build_content_with_trailer("Important body", "decision")
    observations = [_obs(1, "obs-a", "Alpha", content=content)]
    exporter = _exporter(tmp_path, observations)

    result = exporter.export(vault=vault, project="luum-agent-os", write=True)

    assert result.files_written == 1
    exported_path = Path(result.exported_files[0].path)
    text = exported_path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert 'confidence: 0.5' in text
    assert 'decay_class: "decision"' in text
    assert "# Alpha" in text
    assert "Important body" in text
    assert "<engram-lifecycle>" not in text


def test_typed_relations_become_frontmatter_and_wikilinks(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    observations = [
        _obs(1, "obs-a", "Alpha", topic_key="arch/alpha"),
        _obs(2, "obs-b", "Beta", topic_key="arch/beta"),
    ]
    exporter = _exporter(tmp_path, observations)

    result = exporter.export(vault=vault, write=True)

    alpha_path = Path([item.path for item in result.exported_files if item.sync_id == "obs-a"][0])
    text = alpha_path.read_text(encoding="utf-8")
    assert "relations:" in text
    assert "related:" in text
    assert '  - "obs-b"' in text
    assert "## Engram Relations" in text
    assert "- **related**: [[2-arch-beta]]" in text
    assert result.relation_count == 1


def test_rejected_relations_are_excluded(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    observations = [_obs(1, "obs-a", "Alpha"), _obs(2, "obs-b", "Beta")]
    exporter = _exporter(tmp_path, observations, rejected=True)

    result = exporter.export(vault=vault, write=True)

    alpha_path = Path([item.path for item in result.exported_files if item.sync_id == "obs-a"][0])
    text = alpha_path.read_text(encoding="utf-8")
    assert "## Engram Relations" not in text
    assert result.relation_count == 0


def test_since_filter_limits_observations(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    observations = [
        _obs(1, "obs-a", "Old", created_at="2026-01-01T00:00:00Z"),
        _obs(2, "obs-b", "New", created_at="2026-05-05T00:00:00Z"),
    ]
    exporter = _exporter(tmp_path, observations)

    result = exporter.export(vault=vault, since="2026-05-01")

    assert result.files_planned == 1
    assert result.exported_files[0].title == "New"


def test_manifest_skips_unchanged_files_without_force(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    observations = [_obs(1, "obs-a", "Alpha")]
    exporter = _exporter(tmp_path, observations)

    first = exporter.export(vault=vault, write=True)
    second = exporter.export(vault=vault, write=True)
    forced = exporter.export(vault=vault, write=True, force=True)

    assert first.files_written == 1
    assert second.files_written == 0
    assert forced.files_written == 1
