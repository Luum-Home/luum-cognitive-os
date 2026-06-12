"""Regression coverage for the portable plan-feature skill."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = REPO_ROOT / "packages" / "sdd-compound" / "skills" / "plan-feature" / "SKILL.md"
ROOT_SKILL_LINK = REPO_ROOT / "skills" / "plan-feature"


def _skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_plan_feature_is_exposed_as_package_backed_skill() -> None:
    assert SKILL_PATH.exists()
    assert ROOT_SKILL_LINK.is_symlink()
    assert (ROOT_SKILL_LINK / "SKILL.md").resolve() == SKILL_PATH.resolve()


def test_plan_feature_uses_strict_portable_frontmatter() -> None:
    frontmatter = _skill_text().split("---", 2)[1]
    top_level_keys = {
        line.split(":", 1)[0]
        for line in frontmatter.splitlines()
        if line and not line.startswith((" ", "\t")) and ":" in line
    }

    assert top_level_keys == {"name", "description", "metadata"}
    assert "audience: both" in frontmatter
    assert "cos-projected-cli-ide" in frontmatter
    assert "claude-code" not in frontmatter
    assert "context: fork" not in frontmatter
    assert "allowed-tools" not in frontmatter
    assert "disable-model-invocation" not in frontmatter


def test_plan_feature_declares_stack_and_harness_agnostic_behavior() -> None:
    text = _skill_text()

    assert "Use this skill in COS itself and in adopter projects" in text
    assert "projected into any supported CLI or IDE" in text
    assert "Detect stack, surfaces, and local conventions from repository evidence" in text
    assert "Do not invent `npm`, `pytest`, `go test`, Storybook" in text
    assert "Do not implement the feature until" in text


def test_plan_feature_discovers_project_instruction_surfaces_without_claude_only_coupling() -> None:
    text = _skill_text()

    for surface in ("AGENTS.md", ".cognitive-os/", ".claude/", ".codex/", ".opencode/", ".ai/"):
        assert surface in text
    assert ".claude/rules/constitutional-gates.md" not in text
    assert ".claude/sub-rules" not in text


def test_plan_feature_does_not_embed_source_project_specific_assumptions() -> None:
    text = _skill_text().lower()
    banned_fragments = {
        "src/ui",
        "@/ui",
        "firebase",
        "firestore",
        "next-intl",
        "tailwind v4",
        "src/features/<feature>",
        "ai_workflow_document_iso.py",
        "npm run type-check",
        "npm run build",
    }

    assert not {fragment for fragment in banned_fragments if fragment in text}


def test_plan_feature_keeps_bug_and_chore_boundaries() -> None:
    text = _skill_text()

    assert "route to `plan-bug`" in text
    assert "route to `plan-chore`" in text
    assert "root-cause bug fixes" in text
    assert "maintenance chores" in text
