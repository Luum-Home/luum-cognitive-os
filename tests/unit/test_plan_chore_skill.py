"""Regression coverage for the portable plan-chore skill."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = REPO_ROOT / "packages" / "sdd-compound" / "skills" / "plan-chore" / "SKILL.md"
ROOT_SKILL_LINK = REPO_ROOT / "skills" / "plan-chore"


def _skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_plan_chore_is_exposed_as_package_backed_skill() -> None:
    assert SKILL_PATH.exists()
    assert ROOT_SKILL_LINK.is_symlink()
    assert (ROOT_SKILL_LINK / "SKILL.md").resolve() == SKILL_PATH.resolve()


def test_plan_chore_declares_portable_both_scope() -> None:
    text = _skill_text()
    assert "<!-- SCOPE: both -->" in text
    assert "Use this skill in COS itself and in adopter projects" in text
    assert "Do not assume any stack" in text
    assert ".cognitive-os/plans/chores/" in text
    assert "plan-feature or plan-bug" in text


def test_plan_chore_requires_evidence_based_stack_detection() -> None:
    text = _skill_text()
    assert "Detect stack and conventions from files, not assumptions" in text
    assert "Do not invent `npm`, `pytest`, `go test`, or build commands" in text
    assert "If no command is discoverable" in text


def test_plan_chore_does_not_embed_source_project_specific_assumptions() -> None:
    text = _skill_text().lower()
    banned_fragments = {
        "src/ui",
        "@/ui",
        "firebase",
        "firestore",
        ".claude/sub-rules",
        "ai_workflow_document_iso.py",
        "npm run type-check",
        "npm run build",
    }
    assert not (banned_fragments & set(fragment for fragment in banned_fragments if fragment in text))
