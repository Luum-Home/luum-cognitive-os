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


def test_product_answer_skill_forces_cached_adr_282_path_before_broad_docs() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "scripts/cos-product-answer" in text
    assert "scripts/cos-product-answer-refresh" in text
    assert "Do **not** read broad docs" in text
    assert "Source freshness: fresh" in text
    assert "ADR-280/ADR-282" in text
