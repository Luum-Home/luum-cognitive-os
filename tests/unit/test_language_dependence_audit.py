from __future__ import annotations

from pathlib import Path

from lib.language_dependence_audit import audit, extract_regex_literals, structural_risk_score


def _write_skill(root: Path, name: str, patterns: list[str]) -> None:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    routing = "\n".join(
        f"  - pattern: '{pattern}'\n    confidence: 0.90" for pattern in patterns
    )
    (skill_dir / "SKILL.md").write_text(
        f"""---
name: {name}
routing_patterns:
{routing}
---

# {name}
""",
        encoding="utf-8",
    )


def test_extract_regex_literals_ignores_technical_shapes() -> None:
    literals = extract_regex_literals(r"https?://github\.com/[\w.\-]+/[\w.\-]+|\bproduct-answer\b|\bayudar\b")

    assert "ayudar" in literals
    assert "github" not in literals
    assert "product-answer" not in literals


def test_structural_risk_scores_natural_language_intent_above_command_alias() -> None:
    natural = r"\b(ayudar|help|puede|can).{0,40}\b(dev|developer)\b"
    command = r"\bproduct-answer\b"

    assert structural_risk_score(natural, extract_regex_literals(natural)) >= 4
    assert structural_risk_score(command, extract_regex_literals(command)) < 2


def test_audit_flags_natural_language_routing_and_suppresses_low_aliases(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("COS_LANGUAGE_AUDIT_DISABLE_LINGUA", "1")
    _write_skill(
        tmp_path,
        "product-answer",
        [r"\bproduct-answer\b", r"\b(ayudar|help|puede|can).{0,40}\b(dev|developer)\b"],
    )

    report = audit(tmp_path)

    assert report.scanned_patterns == 2
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.primitive == "product-answer"
    assert "ayudar" in finding.extracted_literals
    assert finding.severity in {"medium", "high"}
