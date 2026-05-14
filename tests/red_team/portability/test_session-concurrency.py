# SCOPE: os-only
"""Portability proof for rules/session-concurrency.md."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "rules/session-concurrency.md"


def test_test_session_concurrency_loads_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: documentation primitive must be usable outside the OS repo cwd."""
    target = tmp_path / ARTIFACT.name
    target.write_text(ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")
    text = target.read_text(encoding="utf-8")
    assert "SCOPE: both" in text
    assert str(REPO_ROOT) not in text
