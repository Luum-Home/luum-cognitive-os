from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "pattern-audit" / "SKILL.md"


def test_pattern_audit_is_shared_repo_agnostic_protocol() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "<!-- SCOPE: both -->" in text
    assert "audience: both" in text
    assert "skills/pattern-audit/SKILL.md" not in text
    assert "manifests/" not in text
    assert "docs/02-Decisions/" not in text
    assert ".cognitive-os/" not in text
    assert "/Users/" not in text
    assert "regex/grep across a codebase" in text
    assert "sampling required" in text.lower()
