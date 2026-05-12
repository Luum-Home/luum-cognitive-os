from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "cos-product-answer"


def test_product_answer_cli_answers_differentiator_json() -> None:
    result = subprocess.run(
        [str(CLI), "¿Cuál es nuestro diferenciador?", "--no-cache", "--json"],
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



def test_product_answer_refresh_cli_materializes_and_answer_cli_uses_cache(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cards"
    refresh = subprocess.run(
        [str(ROOT / "scripts" / "cos-product-answer-refresh"), "--question-id", "differentiator", "--cache-dir", str(cache_dir), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    answer = subprocess.run(
        [str(CLI), "¿Cuál es nuestro diferenciador?", "--cache-dir", str(cache_dir), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert refresh.returncode == 0
    refresh_report = json.loads(refresh.stdout)
    assert refresh_report["adr"] == "ADR-282"
    assert refresh_report["refreshed_count"] == 1
    assert (cache_dir / "differentiator.md").exists()
    assert (cache_dir / "differentiator.json").exists()
    assert (cache_dir / "index.yaml").exists()

    assert answer.returncode == 0
    answer_report = json.loads(answer.stdout)
    assert answer_report["cache"]["mode"] == "card"
    assert answer_report["cache"]["freshness"] == "fresh"
    assert answer_report["question_id"] == "differentiator"


def test_product_answer_cli_no_cache_forces_live_generation_after_refresh(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cards"
    subprocess.run(
        [str(ROOT / "scripts" / "cos-product-answer-refresh"), "--question-id", "differentiator", "--cache-dir", str(cache_dir)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    result = subprocess.run(
        [str(CLI), "--question-id", "differentiator", "--cache-dir", str(cache_dir), "--no-cache", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["cache"]["mode"] == "live"
    assert report["question_id"] == "differentiator"
