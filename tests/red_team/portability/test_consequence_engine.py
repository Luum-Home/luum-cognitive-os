# SCOPE: os-only
"""Portability proof for cos_lib/consequence_engine.py.

Pins that ``ConsequenceEngine`` evaluates performance records and persists
its history using only the caller-supplied ``history_path`` — a relative
``.cognitive-os/metrics/...`` layout every consumer project has, not a path
into the Cognitive OS source repo — when the process cwd is an unrelated
arbitrary directory.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/consequence_engine.py"


def _load_module(monkeypatch, cwd: Path):
    monkeypatch.chdir(cwd)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_consequence_engine", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_consequence_engine_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    _load_module(monkeypatch, tmp_path)


def test_consequence_engine_evaluates_and_persists_from_arbitrary_cwd(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: evaluate()/apply_consequence()/get_skills_needing_rewrite()
    must exercise real scoring + JSONL persistence using only the caller-supplied
    history_path, from a cwd that shares no relationship with the OS repo or the
    consumer project directory.
    """
    unrelated_cwd = tmp_path / "somewhere-else"
    unrelated_cwd.mkdir()
    history_path = tmp_path / "consumer-project" / ".cognitive-os" / "metrics" / "consequence-history.jsonl"

    module = _load_module(monkeypatch, unrelated_cwd)
    ConsequenceEngine = module.ConsequenceEngine
    PerformanceRecord = module.PerformanceRecord
    Consequence = module.Consequence

    engine = ConsequenceEngine(history_path=str(history_path))

    now = datetime.now(timezone.utc).isoformat()

    def record(score: float, success: bool) -> "PerformanceRecord":
        return PerformanceRecord(
            agent_or_skill="portability-probe-skill",
            task_type="unit-test",
            trust_score=score,
            success=success,
            cost_usd=0.01,
            tokens_used=100,
            retries=0,
            timestamp=now,
        )

    # First low score -> WARN
    action = engine.evaluate(record(40.0, False))
    assert action.consequence == Consequence.WARN

    # Second consecutive low score -> DEGRADE
    action = engine.evaluate(record(35.0, False))
    assert action.consequence == Consequence.DEGRADE
    actions_taken = engine.apply_consequence(action)
    assert any("Degraded" in a for a in actions_taken)

    # Third consecutive low score -> DISABLE
    action = engine.evaluate(record(20.0, False))
    assert action.consequence == Consequence.DISABLE
    engine.apply_consequence(action)

    # History must have been persisted as real JSONL on disk, not in-memory only.
    assert history_path.exists()
    assert history_path.read_text(encoding="utf-8").strip() != ""

    assert engine.is_skill_disabled("portability-probe-skill") is True

    rewrite_candidates = engine.get_skills_needing_rewrite(
        metrics_dir=str(history_path.parent), threshold=3, hours=24
    )
    names = [c["skill_name"] for c in rewrite_candidates]
    assert "portability-probe-skill" in names
