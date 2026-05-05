"""Behavior tests for the governed self-improvement CLI."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "cos_governed_self_improvement.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _run(project_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(project_dir), *args],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=20,
    )


def test_cli_suggest_draft_inspect_and_promote(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / ".cognitive-os" / "metrics" / "error-learning.jsonl",
        [
            {"type": "TEST_FAILURE", "service": "checkout"},
            {"type": "TEST_FAILURE", "service": "checkout"},
            {"type": "TEST_FAILURE", "service": "checkout"},
        ],
    )

    suggest = _run(tmp_path, "suggest")
    assert suggest.returncode == 0, suggest.stderr
    signals = json.loads(suggest.stdout)
    assert signals[0]["slug"] == "repair-test-failure-checkout"

    draft = _run(tmp_path, "draft", "repair-test-failure-checkout")
    assert draft.returncode == 0, draft.stderr
    draft_payload = json.loads(draft.stdout)
    assert draft_payload["status"] == "draft"

    inspect = _run(tmp_path, "inspect", "repair-test-failure-checkout")
    assert inspect.returncode == 0, inspect.stderr
    assert json.loads(inspect.stdout)["draft_id"] == "repair-test-failure-checkout"

    denied = _run(tmp_path, "promote", "repair-test-failure-checkout")
    assert denied.returncode != 0
    assert "promotion requires" in denied.stderr

    unevaluated = _run(
        tmp_path,
        "promote",
        "repair-test-failure-checkout",
        "--approved-by",
        "behavior-test",
    )
    assert unevaluated.returncode != 0
    assert "comparative primitive evaluation" in unevaluated.stderr

    failed_evaluation = _run(
        tmp_path,
        "evaluate",
        "repair-test-failure-checkout",
        "--baseline-score",
        "90",
        "--candidate-score",
        "90",
        "--safety-regression",
        "new guard false positive",
    )
    assert failed_evaluation.returncode == 0, failed_evaluation.stderr
    assert json.loads(failed_evaluation.stdout)["status"] == "failed"

    blocked = _run(
        tmp_path,
        "promote",
        "repair-test-failure-checkout",
        "--approved-by",
        "behavior-test",
    )
    assert blocked.returncode != 0
    assert "promotion evaluation failed" in blocked.stderr

    passed_evaluation = _run(
        tmp_path,
        "evaluate",
        "repair-test-failure-checkout",
        "--baseline-score",
        "88",
        "--candidate-score",
        "91",
        "--evidence-command",
        "python3 -m pytest tests/unit/test_governed_self_improvement.py -q",
    )
    assert passed_evaluation.returncode == 0, passed_evaluation.stderr
    assert json.loads(passed_evaluation.stdout)["status"] == "passed"

    promoted = _run(
        tmp_path,
        "promote",
        "repair-test-failure-checkout",
        "--approved-by",
        "behavior-test",
    )
    assert promoted.returncode == 0, promoted.stderr
    payload = json.loads(promoted.stdout)
    assert payload["target"] == ".cognitive-os/skills/cos/repair-test-failure-checkout/SKILL.md"
    assert payload["promotion_evaluation"]["candidate_score"] > payload["promotion_evaluation"]["baseline_score"]
    assert (tmp_path / payload["target"]).exists()
