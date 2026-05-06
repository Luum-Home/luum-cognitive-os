"""Unit tests for scripts/cos_promotion_proposer.py — ADR-178.

Synthetic SkillStore fixture: skills above and below threshold are evaluated.
Asserts proposal artifacts are created only for above-threshold skills, and
that primitive-lifecycle.yaml is NEVER mutated.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.skill_store import SkillStore  # noqa: E402
from scripts.cos_promotion_proposer import evaluate, main  # noqa: E402


@pytest.fixture
def synth_store(tmp_path: Path) -> Path:
    """Create a SkillStore with one above-threshold and one below-threshold skill."""
    db = tmp_path / "store.db"
    store = SkillStore(db)
    # high-evidence skill: 60 records, all success, 5 positive judgments
    for _ in range(60):
        store.record_execution("good-skill", "session-x", 1, 100, "success")
    for _ in range(5):
        store.record_judgment(
            hashlib.sha256(b"good-skill").hexdigest(),
            "judge-v1",
            "approve",
            0.9,
            "looks good",
        )
    # low-evidence skill: 5 records only
    for _ in range(5):
        store.record_execution("weak-skill", "session-x", 1, 100, "success")
    store.close()
    return db


@pytest.fixture
def synth_lifecycle(tmp_path: Path) -> Path:
    """Minimal primitive-lifecycle.yaml with two sandbox primitives."""
    p = tmp_path / "primitive-lifecycle.yaml"
    p.write_text(
        "schema_version: 1\n"
        "primitives:\n"
        "- id: skills/good-skill\n"
        "  kind: skill\n"
        "  lifecycle_state: sandbox\n"
        "  maturity: advisory\n"
        "  distribution: lab\n"
        "- id: skills/weak-skill\n"
        "  kind: skill\n"
        "  lifecycle_state: sandbox\n"
        "  maturity: advisory\n"
        "  distribution: lab\n"
        "- id: skills/already-advisory\n"
        "  kind: skill\n"
        "  lifecycle_state: advisory\n"
        "  maturity: advisory\n"
        "  distribution: lab\n",
        encoding="utf-8",
    )
    return p


def test_evaluate_separates_eligible_from_ineligible(synth_store: Path, synth_lifecycle: Path):
    from scripts.cos_promotion_proposer import _load_lifecycle

    prims = _load_lifecycle(synth_lifecycle)
    thresholds = {"records": 50, "success": 0.85, "judge": 0.8}
    results = evaluate(prims, synth_store, thresholds)
    by_name = {r["name"]: r for r in results}
    assert "good-skill" in by_name
    assert "weak-skill" in by_name
    # advisory primitive must be skipped (sandbox-only)
    assert "already-advisory" not in by_name
    assert by_name["good-skill"]["eligible"] is True
    assert by_name["weak-skill"]["eligible"] is False


def test_apply_writes_proposals_only_for_eligible(
    tmp_path: Path, synth_store: Path, synth_lifecycle: Path, capsys
):
    out_root = tmp_path / "proposals"
    metrics = tmp_path / "metrics.jsonl"
    rc = main(
        [
            "--db", str(synth_store),
            "--lifecycle", str(synth_lifecycle),
            "--out-root", str(out_root),
            "--metrics", str(metrics),
            "--apply",
        ]
    )
    assert rc == 0

    # exactly one proposal artifact (good-skill); none for weak-skill.
    written = list(out_root.rglob("*.md"))
    assert len(written) == 1, f"expected 1 proposal, got {written}"
    assert written[0].name == "good-skill.md"

    # metrics emitted
    assert metrics.exists()
    line = metrics.read_text(encoding="utf-8").strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["kind"] == "promotion-proposer-run"
    assert payload["eligible"] == 1
    assert payload["written"] == 1


def test_dry_run_writes_nothing(tmp_path: Path, synth_store: Path, synth_lifecycle: Path):
    out_root = tmp_path / "proposals"
    metrics = tmp_path / "metrics.jsonl"
    rc = main(
        [
            "--db", str(synth_store),
            "--lifecycle", str(synth_lifecycle),
            "--out-root", str(out_root),
            "--metrics", str(metrics),
            # default is --dry-run; no --apply
        ]
    )
    assert rc == 0
    assert not list(out_root.rglob("*.md"))
    # metrics still records the run
    assert metrics.exists()


def test_killswitch_short_circuits(monkeypatch, tmp_path: Path, synth_lifecycle: Path):
    monkeypatch.setenv("DISABLE_PROMOTION_PROPOSER", "1")
    rc = main(["--lifecycle", str(synth_lifecycle), "--metrics", str(tmp_path / "m.jsonl")])
    assert rc == 0


def test_manifest_not_mutated_by_apply(synth_store: Path, synth_lifecycle: Path, tmp_path: Path):
    before = synth_lifecycle.read_bytes()
    main(
        [
            "--db", str(synth_store),
            "--lifecycle", str(synth_lifecycle),
            "--out-root", str(tmp_path / "proposals"),
            "--metrics", str(tmp_path / "m.jsonl"),
            "--apply",
        ]
    )
    after = synth_lifecycle.read_bytes()
    assert before == after, "promoter must not mutate lifecycle manifest"
