"""Portability checks for dod-check profile adoption."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "packages" / "quality-gates" / "skills" / "dod-check" / "SKILL.md"
PROFILES = REPO_ROOT / "packages" / "quality-gates" / "skills" / "dod-check" / "references" / "dod-profiles.md"


def test_dod_check_uses_strict_frontmatter_with_metadata() -> None:
    frontmatter = SKILL.read_text(encoding="utf-8").split("---", 2)[1]
    top_level = {
        line.split(":", 1)[0]
        for line in frontmatter.splitlines()
        if line and not line.startswith((" ", "\t")) and ":" in line
    }
    assert top_level == {"name", "description", "metadata"}
    assert "backend, frontend, UI component, or Storybook" in frontmatter


def test_dod_profiles_are_stack_agnostic_overlays() -> None:
    text = PROFILES.read_text(encoding="utf-8")
    for profile in ("Backend API / Server Work", "Frontend Feature / App Work", "UI Component / Design-System Work", "Storybook / Component Documentation Work"):
        assert profile in text
    assert "They are portable categories, not stack mandates" in text
    assert "Do not copy these bullets into a PR blindly" in text


def test_dod_profiles_do_not_embed_source_project_stack_policy() -> None:
    combined = (SKILL.read_text(encoding="utf-8") + "\n" + PROFILES.read_text(encoding="utf-8")).lower()
    banned = {
        "firebase",
        "firestore",
        "next-intl",
        "tailwind v4",
        "@/ui",
        ".claude/sub-rules",
        "vault/03-design",
        "vault/04-development",
        "src/features/<feature>",
    }
    assert not {fragment for fragment in banned if fragment in combined}
