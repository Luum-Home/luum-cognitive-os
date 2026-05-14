# SCOPE: os-only
"""Portability proof for skills/agent-dashboard/SKILL.md."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "skills/agent-dashboard/SKILL.md"


def test_skill_agent_dashboard_skill_loads_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: skill metadata must be usable outside the OS repo cwd."""
    target = tmp_path / ".codex" / "skills" / "agent-dashboard"
    target.mkdir(parents=True)
    copied = target / "SKILL.md"
    copied.write_text(ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")
    text = copied.read_text(encoding="utf-8")
    assert "name:" in text
    assert str(REPO_ROOT) not in text
