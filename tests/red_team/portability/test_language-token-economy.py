# SCOPE: os-only
"""Portability proof for rules/language-token-economy.md."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RULE = REPO_ROOT / "rules/language-token-economy.md"


def test_language_token_economy_rule_is_project_portable() -> None:
    text = RULE.read_text(encoding="utf-8")
    assert "<!-- SCOPE: both -->" in text
    assert "## Contextual Trigger" in text
    assert "Preserve the user's language" in text
    assert ".cognitive-os/" not in text
    assert "docs/02-Decisions" not in text
