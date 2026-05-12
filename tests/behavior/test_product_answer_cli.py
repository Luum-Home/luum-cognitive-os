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


def test_product_answer_cli_competitors_uses_local_radar_before_browsing() -> None:
    result = subprocess.run(
        [str(CLI), "--question-id", "competitors", "--no-cache", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["question_id"] == "competitors"
    assert "local Tech Radar" in report["answer_long"]
    assert "Use internet research only for volatile" in report["answer_long"]
    assert "docs/reports/external-tools-radar-INDEX.md" in report["approved_sources"]
    assert "docs/vs-alternatives.md" in report["approved_sources"]
    assert "docs/component-sources.md" in report["approved_sources"]
    assert any(
        "Do not browse by default" in boundary
        for claim in report["claims"]
        for boundary in claim["boundaries"]
    )


def test_product_answer_cli_routes_vanilla_usage_question() -> None:
    result = subprocess.run(
        [str(CLI), "cuando uso configuraciones vanilla sin cognitive os", "--no-cache", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["question_id"] == "vanilla_usage"
    assert "Use vanilla IDE-agent setups" in report["answer_short"]
    assert "docs/business/cos-vs-vanilla-dx-review.md" in report["approved_sources"]
    assert any(claim["claim_id"] == "vanilla_boundary" for claim in report["claims"])
    assert "COS is always better than vanilla IDE agents" in report["unsafe_claims_to_avoid"]


def test_product_answer_cli_routes_runtime_surface_question() -> None:
    result = subprocess.run(
        [str(CLI), "puede correr como servicio tiene ui y cli", "--no-cache", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["question_id"] == "runtime_surfaces"
    assert "operator CLI" in report["answer_long"]
    assert "docs/adrs/ADR-211-service-mode-readiness-gate.md" in report["approved_sources"]
    assert any(claim["claim_id"] == "service_mode_readiness_partial" for claim in report["claims"])
    assert "COS is already a polished SaaS dashboard" in report["unsafe_claims_to_avoid"]


def test_product_answer_cli_routes_alternative_choice_question() -> None:
    result = subprocess.run(
        [str(CLI), "por que no uso hermes en su lugar", "--no-cache", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["question_id"] == "alternatives_choice"
    assert "Use Hermes, Agent Zero, or OpenClaw" in report["answer_short"]
    assert "docs/vs-alternatives.md" in report["approved_sources"]
    assert any(claim["claim_id"] == "alternative_complementarity" for claim in report["claims"])
    assert "browse only for volatile current facts" in report["answer_long"]
