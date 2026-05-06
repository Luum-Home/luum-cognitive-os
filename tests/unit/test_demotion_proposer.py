"""Unit tests for scripts/cos_demotion_proposer.py — ADR-178.

Skills with zero recent records get demotion proposals; active skills do not.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.skill_store import SkillStore  # noqa: E402
from scripts.cos_demotion_proposer import evaluate, main, _load_lifecycle  # noqa: E402


@pytest.fixture
def lifecycle_with_advisory(tmp_path: Path) -> Path:
    p = tmp_path / "primitive-lifecycle.yaml"
    p.write_text(
        "schema_version: 1\n"
        "primitives:\n"
        "- id: skills/dormant-skill\n"
        "  kind: skill\n"
        "  lifecycle_state: advisory\n"
        "  maturity: advisory\n"
        "  distribution: lab\n"
        "- id: skills/active-skill\n"
        "  kind: skill\n"
        "  lifecycle_state: advisory\n"
        "  maturity: advisory\n"
        "  distribution: lab\n"
        "- id: skills/sandbox-skill\n"
        "  kind: skill\n"
        "  lifecycle_state: sandbox\n"
        "  maturity: advisory\n"
        "  distribution: lab\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def store_with_active(tmp_path: Path) -> Path:
    db = tmp_path / "store.db"
    s = SkillStore(db)
    s.record_execution("active-skill", "session-x", 1, 100, "success")
    s.close()
    return db


def test_evaluate_flags_zero_record_advisory(lifecycle_with_advisory: Path, store_with_active: Path):
    prims = _load_lifecycle(lifecycle_with_advisory)
    results = evaluate(prims, store_with_active, window_days=90)
    by_name = {r["name"]: r for r in results}
    assert by_name["dormant-skill"]["eligible"] is True
    assert by_name["active-skill"]["eligible"] is False
    # sandbox-skill must not appear (advisory/blocking only)
    assert "sandbox-skill" not in by_name


def test_evaluate_uses_windowed_skillstore_events_for_demotion(
    lifecycle_with_advisory: Path, tmp_path: Path
):
    db = tmp_path / "store.db"
    store = SkillStore(db)
    store.record_execution("active-skill", "session-x", 1, 100, "success")
    store.close()
    conn = sqlite3.connect(str(db))
    conn.execute("UPDATE skill_execution_events SET timestamp = ?", ("2026-03-07T12:00:00+00:00",))
    conn.commit()
    conn.close()

    prims = _load_lifecycle(lifecycle_with_advisory)
    results = evaluate(prims, db, window_days=90)
    by_name = {r["name"]: r for r in results}

    assert by_name["active-skill"]["recent_records"] == 1
    assert by_name["active-skill"]["eligible"] is False


def test_apply_writes_demotion_proposals(
    lifecycle_with_advisory: Path, store_with_active: Path, tmp_path: Path
):
    out_root = tmp_path / "demotions"
    metrics = tmp_path / "demotion-metrics.jsonl"
    rc = main(
        [
            "--db", str(store_with_active),
            "--lifecycle", str(lifecycle_with_advisory),
            "--out-root", str(out_root),
            "--metrics", str(metrics),
            "--apply",
        ]
    )
    assert rc == 0
    written = list(out_root.rglob("*.md"))
    assert len(written) == 1
    assert written[0].name == "dormant-skill.md"

    payload = json.loads(metrics.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert payload["kind"] == "demotion-proposer-run"
    assert payload["eligible"] == 1


def test_manifest_not_mutated(lifecycle_with_advisory: Path, store_with_active: Path, tmp_path: Path):
    before = lifecycle_with_advisory.read_bytes()
    main(
        [
            "--db", str(store_with_active),
            "--lifecycle", str(lifecycle_with_advisory),
            "--out-root", str(tmp_path / "out"),
            "--metrics", str(tmp_path / "m.jsonl"),
            "--apply",
        ]
    )
    assert lifecycle_with_advisory.read_bytes() == before
