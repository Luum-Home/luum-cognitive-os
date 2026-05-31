"""Portability proofs for the publication-safety agentic primitive."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def test_publication_safety_hook_is_project_configured_not_repo_hardcoded() -> None:
    text = (REPO / "hooks" / "publication-safety.sh").read_text(encoding="utf-8")
    assert "COS_PUBLICATION_SAFETY_CONFIG" in text
    assert "scripts/pre-publication-gate" not in text
    assert "luum-agent-harness" not in text


def test_publication_safety_cli_is_project_configured_not_repo_hardcoded() -> None:
    text = (REPO / "scripts" / "cos-publication-safety").read_text(encoding="utf-8")
    assert "lib.publication_safety" in text
    assert "scripts/pre-publication-gate" not in text
    assert "luum-agent-harness" not in text
