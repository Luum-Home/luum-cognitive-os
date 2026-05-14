# SCOPE: os-only
"""Load characterization for the os-only skills/add-hook/SKILL.md metadata."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "skills/add-hook/SKILL.md"


def test_skill_add_hook_skill_loads_from_arbitrary_project_root(tmp_path: Path) -> None:
    """The skill file remains structurally loadable even though its procedure is COS-specific."""
    target = tmp_path / ".codex" / "skills" / "add-hook"
    target.mkdir(parents=True)
    copied = target / "SKILL.md"
    copied.write_text(ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")
    text = copied.read_text(encoding="utf-8")
    assert "name:" in text
    assert str(REPO_ROOT) not in text
