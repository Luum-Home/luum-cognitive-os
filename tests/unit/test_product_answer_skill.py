from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "product-answer" / "SKILL.md"


def _frontmatter() -> dict:
    text = SKILL.read_text(encoding="utf-8")
    stripped = text.split("-->", 1)[1].lstrip() if text.startswith("<!--") else text
    assert stripped.startswith("---\n")
    raw = stripped.split("---\n", 2)[1]
    payload = yaml.safe_load(raw)
    assert isinstance(payload, dict)
    return payload


def test_product_answer_skill_is_os_only_and_routes_commercial_questions() -> None:
    fm = _frontmatter()
    text = SKILL.read_text(encoding="utf-8")

    assert fm["name"] == "product-answer"
    assert fm["audience"] == "os-dev"
    assert "SCOPE: os-only" in text
    assert "diferenciador" in text
    assert "pricing" in text
    assert "competitors" in text
    assert "vanilla" in text
    assert "CLI/UI/service/headless" in text


def test_product_answer_skill_forces_cached_adr_282_path_before_broad_docs() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "scripts/cos-product-answer" in text
    assert "scripts/cos-product-answer-refresh" in text
    assert "Do **not** read broad docs" in text
    assert "Source freshness: fresh" in text
    assert "ADR-280/ADR-282" in text


def test_product_answer_skill_checks_local_tool_radar_before_internet() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "Tool and competitor grounding order" in text
    assert "docs/06-Daily/reports/external-tools-radar-INDEX.md" in text
    assert "manifests/external-tools-adoption.yaml" in text
    assert "manifests/feature-tool-due-diligence.yaml" in text
    assert "docs/08-References/root/vs-alternatives.md" in text
    assert "Only then browse" in text
    assert "first move\n  is the local radar, not internet search" in text
    assert "https://deepwiki.com/<owner>/<repo>" in text
    assert "/repo-scout" in text
    assert "/deep-tool-research" in text


def test_product_answer_skill_lists_new_product_question_cards() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "`vanilla_usage`" in text
    assert "`runtime_surfaces`" in text
    assert "`alternatives_choice`" in text
