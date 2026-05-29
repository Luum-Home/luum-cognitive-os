from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.improve_loop import build_context, build_feedback, load_task, run_improvement_loop

REPO = Path(__file__).resolve().parents[2]
TASK = REPO / "benchmarks" / "improvement" / "skip-classification-mini"


def test_load_task_requires_contract(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="benchmark task contract missing"):
        load_task(tmp_path)


def test_run_improvement_loop_writes_generation_artifacts(tmp_path: Path) -> None:
    report_dir = tmp_path / ".cognitive-os" / "reports"
    report_dir.mkdir(parents=True)
    (report_dir / "sample.md").write_text("# sample\n", encoding="utf-8")

    summary = run_improvement_loop(tmp_path, TASK, run_id="unit-smoke", max_gen=1)

    run_dir = tmp_path / ".cognitive-os" / "improvement-runs" / "unit-smoke"
    gen_dir = run_dir / "gen_1"
    assert summary["schema_version"] == "cos-improve.v1"
    assert summary["generations"][0]["passed"] is True
    for name in ["target", "agent_execution.jsonl", "evaluation.json", "improvement.md", "patch.diff"]:
        assert (gen_dir / name).exists()
    evaluation = json.loads((gen_dir / "evaluation.json").read_text(encoding="utf-8"))
    assert evaluation["metrics"]["accuracy"] == 1.0

    feedback = build_feedback(tmp_path, "unit-smoke")
    assert feedback["gate"] == {"auto_apply": False, "human_approval_required": True}
    assert feedback["proposals"] == []
    assert (gen_dir / "feedback.md").exists()

    context = build_context(tmp_path, "unit-smoke")
    assert "Engram Integration" in context
    assert ".cognitive-os/reports/sample.md" in context
