from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "cos-product-answer"


def test_product_answer_cli_answers_differentiator_json() -> None:
    result = subprocess.run(
        [str(CLI), "¿Cuál es nuestro diferenciador?", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["schema_version"] == "product-answer-report/v1"
    assert report["adr"] == "ADR-280"
    assert report["question_id"] == "differentiator"
    assert "behavioral governance" in report["answer_short"]
    assert report["unsafe_claims_to_avoid"]
    assert report["claims"]


def test_product_answer_cli_renders_markdown_by_question_id() -> None:
    result = subprocess.run(
        [str(CLI), "--question-id", "landing_pitch", "--format", "markdown"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "# Product Answer: landing_pitch" in result.stdout
    assert "AI agents ship faster. Cognitive OS makes them prove it." in result.stdout
    assert "TRUST_REPORT:" in result.stdout


def test_product_answer_cli_unknown_question_fails() -> None:
    result = subprocess.run(
        [str(CLI), "unmatched procurement policy", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert "no product question matched" in report["error"]
