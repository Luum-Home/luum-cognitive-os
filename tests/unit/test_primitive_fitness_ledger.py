"""Tests for primitive fitness ledger aggregation."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

MODULE = Path(__file__).resolve().parents[2] / "scripts" / "primitive_fitness_ledger.py"
spec = importlib.util.spec_from_file_location("primitive_fitness_ledger", MODULE)
assert spec and spec.loader
primitive_fitness_ledger = importlib.util.module_from_spec(spec)
sys.modules["primitive_fitness_ledger"] = primitive_fitness_ledger
spec.loader.exec_module(primitive_fitness_ledger)


def write_report(path: Path, primitive_id: str, verdict: str, candidate: float, baseline: float = 80.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "primitive-fitness.v1",
                "primitive_id": primitive_id,
                "verdict": verdict,
                "status": "pass" if verdict == "promote" else "needs_evidence",
                "delta": round(candidate - baseline, 2),
                "required_delta": 1.0,
                "baseline": {"overall_score": baseline, "sample_count": 3},
                "candidate": {"overall_score": candidate, "sample_count": 4},
                "missing_signals": [] if verdict == "promote" else ["quality"],
                "safety_regressions": [],
                "evidence_commands": ["scripts/cos-primitive-fitness --json"],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_build_ledger_groups_reports_by_family(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    skills = write_report(root / "docs" / "06-Daily" / "reports" / "primitive-fitness" / "skill.json", "skills/example/SKILL.md", "promote", 86)
    hooks = write_report(root / "custom" / "hook.json", "hooks/pre-tool.sh", "needs_evidence", 81)

    payload = primitive_fitness_ledger.build_ledger(root, [str(hooks)])

    assert payload["schema_version"] == "primitive-fitness-ledger.v1"
    assert payload["summary"]["total_reports"] == 2
    assert payload["summary"]["families"]["skills"]["promote"] == 1
    assert payload["summary"]["families"]["hooks"]["needs_evidence"] == 1
    ids = {row["primitive_id"] for row in payload["items"]}
    assert ids == {"skills/example/SKILL.md", "hooks/pre-tool.sh"}
    assert skills.exists()


def test_markdown_renders_empty_ledger() -> None:
    payload = primitive_fitness_ledger.build_ledger(Path("/tmp/does-not-exist"), [])
    markdown = primitive_fitness_ledger.render_markdown(payload)

    assert "Primitive Fitness Ledger" in markdown
    assert "no primitive fitness reports found" in markdown
