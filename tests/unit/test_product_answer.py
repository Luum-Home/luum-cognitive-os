from __future__ import annotations

from pathlib import Path

import pytest

from lib.product_answer import (
    ProductAnswerError,
    build_answer,
    card_freshness,
    load_cached_answer,
    refresh_answer_cards,
    render_markdown,
    select_question,
)


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def _project(tmp_path: Path) -> Path:
    _write(
        tmp_path / "manifests" / "product-question-bank.yaml",
        """
schema_version: product-question-bank/v1
default_question_id: differentiator
questions:
  differentiator:
    category: positioning
    aliases: [diferenciador, what is our differentiator]
    keywords: [diferenciador, differentiator]
    approved_sources: [docs/source.md]
    related_claims: [claim_real, claim_partial]
    answer_short: Short answer.
    answer_long: Long answer.
    recommended_pitch: Agents ship faster. COS makes them prove it.
    unsafe_claims_to_avoid: [universal parity]
    gaps: [fresh competitor research]
  automation_gap:
    category: automation
    aliases: [se puede automatizar]
    keywords: [automatizar]
    approved_sources: [docs/source.md]
    related_claims: [claim_real]
    answer_short: Automation answer.
    answer_long: Automation long answer.
    recommended_pitch: Trust-backed messaging.
    unsafe_claims_to_avoid: []
    gaps: []
""",
    )
    _write(
        tmp_path / "manifests" / "product-claim-evidence.yaml",
        """
schema_version: product-claim-evidence/v1
status_order: [real, partial-real, partial, aspirational, blocked]
claims:
  claim_real:
    status: real
    maturity: implemented
    confidence: 0.9
    summary: Real claim.
    approved_wording: Real wording.
    evidence: [docs/source.md]
    boundaries: [stay scoped]
  claim_partial:
    status: partial
    maturity: partial_runtime
    confidence: 0.7
    summary: Partial claim.
    approved_wording: Partial wording.
    evidence: [docs/source.md]
    boundaries: [do not overclaim]
""",
    )
    _write(tmp_path / "docs" / "source.md", "# Source")
    return tmp_path


def test_select_question_matches_spanish_alias(tmp_path: Path) -> None:
    project = _project(tmp_path)
    report = build_answer(project, question_text="¿Cuál es nuestro diferenciador?")

    assert report["question_id"] == "differentiator"
    assert report["status"] == "warn"
    assert report["claim_status"] == "partial"
    assert report["trust_report"]["evidence_count"] == 1
    assert "universal parity" in report["unsafe_claims_to_avoid"]


def test_select_question_by_explicit_id(tmp_path: Path) -> None:
    project = _project(tmp_path)
    report = build_answer(project, question_id="automation_gap")

    assert report["question_id"] == "automation_gap"
    assert report["status"] == "pass"
    assert report["claim_status"] == "real"
    assert report["recommended_pitch"] == "Trust-backed messaging."


def test_missing_evidence_fails_report(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / "docs" / "source.md").unlink()

    report = build_answer(project, question_id="differentiator")

    assert report["status"] == "fail"
    assert report["confidence"] <= 0.5
    assert any("missing evidence paths" in finding for finding in report["findings"])


def test_blocked_claim_fails_strict_and_non_strict(tmp_path: Path) -> None:
    project = _project(tmp_path)
    claim_file = project / "manifests" / "product-claim-evidence.yaml"
    claim_file.write_text(
        claim_file.read_text(encoding="utf-8").replace("status: partial", "status: blocked"),
        encoding="utf-8",
    )

    report = build_answer(project, question_id="differentiator")

    assert report["status"] == "fail"
    assert "selected answer references blocked claims" in report["findings"]


def test_unknown_question_raises_clear_error(tmp_path: Path) -> None:
    project = _project(tmp_path)

    with pytest.raises(ProductAnswerError, match="no product question matched"):
        build_answer(project, question_text="unrelated procurement policy")


def test_render_markdown_includes_trust_report(tmp_path: Path) -> None:
    project = _project(tmp_path)
    report = build_answer(project, question_id="automation_gap")

    markdown = render_markdown(report)

    assert "# Product Answer: automation_gap" in markdown
    assert "TRUST_REPORT:" in markdown
    assert "Trust-backed messaging." in markdown


def test_select_question_rejects_unknown_id(tmp_path: Path) -> None:
    _project(tmp_path)
    bank = {
        "questions": {
            "known": {"aliases": [], "keywords": []},
        }
    }

    with pytest.raises(ProductAnswerError, match="unknown question id"):
        select_question(bank, question_id="missing")



def test_refresh_answer_cards_writes_card_index_and_cached_report(tmp_path: Path) -> None:
    project = _project(tmp_path)

    refresh = refresh_answer_cards(project, question_id="differentiator")
    cached = load_cached_answer(project, question_text="factor diferenciador")

    assert refresh["status"] == "pass"
    assert refresh["refreshed_count"] == 1
    assert (project / ".cognitive-os" / "product-answers" / "differentiator.md").exists()
    assert (project / ".cognitive-os" / "product-answers" / "differentiator.json").exists()
    assert (project / ".cognitive-os" / "product-answers" / "index.yaml").exists()
    assert cached is not None
    assert cached["cache"]["mode"] == "card"
    assert cached["cache"]["freshness"] == "fresh"
    assert cached["question_id"] == "differentiator"


def test_card_freshness_detects_source_drift(tmp_path: Path) -> None:
    project = _project(tmp_path)
    refresh_answer_cards(project, question_id="differentiator")

    before = card_freshness(project, "differentiator")
    (project / "docs" / "source.md").write_text("# Source changed\n", encoding="utf-8")
    after = card_freshness(project, "differentiator")
    cached = load_cached_answer(project, question_id="differentiator")

    assert before["freshness"] == "fresh"
    assert after["freshness"] == "stale"
    assert "docs/source.md" in after["changed_sources"]
    assert cached is None
