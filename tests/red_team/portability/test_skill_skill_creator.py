# SCOPE: os-only
"""Portability proof for skills/skill-creator/SKILL.md."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "skills/skill-creator/SKILL.md"


def _text() -> str:
    return ARTIFACT.read_text(encoding="utf-8")


def test_skill_skill_creator_skill_loads_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: skill metadata must be usable outside the OS repo cwd."""
    target = tmp_path / ".codex" / "skills" / "skill-creator"
    target.mkdir(parents=True)
    copied = target / "SKILL.md"
    copied.write_text(_text(), encoding="utf-8")
    text = copied.read_text(encoding="utf-8")
    assert "name: skill-creator" in text
    assert str(REPO_ROOT) not in text


def test_skill_creator_accepts_metaprompt_workflow_without_claude_only_coupling() -> None:
    text = _text()
    lowered = text.lower()

    assert "metaprompt-workflow" in text
    assert "create or update portable ai agent skills" in lowered
    assert "do not assume `.claude/skills/` is the only target" in lowered
    assert "mandatory web/documentation fetching unless current external documentation" in lowered
    assert "cos package" not in lowered


def test_skill_creator_preserves_strict_frontmatter_with_metadata_extensions() -> None:
    text = _text()
    frontmatter = text.split("---", 2)[1]
    top_level_keys = {
        line.split(":", 1)[0]
        for line in frontmatter.splitlines()
        if line and not line.startswith((" ", "\t")) and ":" in line
    }
    assert top_level_keys == {"name", "description", "metadata"}
    assert "version: 1.2.0" in frontmatter
    assert "audience: both" in frontmatter
