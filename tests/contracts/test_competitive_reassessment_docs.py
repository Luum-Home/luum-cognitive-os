"""Contract tests for the OpenClaw/Hermes competitive reassessment."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC = PROJECT_ROOT / "docs" / "08-References" / "business" / "competitive-reassessment-openclaw-hermes-2026-04.md"


def _table_rows(markdown: str, heading: str) -> list[list[str]]:
    lines = markdown.splitlines()
    start = lines.index(heading)
    rows: list[list[str]] = []
    for line in lines[start + 1 :]:
        if line.startswith("## ") or line.startswith("### "):
            break
        if not line.startswith("|") or "---" in line:
            continue
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def test_competitive_reassessment_is_linked_from_product_entrypoints() -> None:
    assert "business/competitive-reassessment-openclaw-hermes-2026-04.md" in (
        PROJECT_ROOT / "docs" / "00-MOCs" / "entrypoints" / "README.md"
    ).read_text(encoding="utf-8")
    assert "competitive-reassessment-openclaw-hermes-2026-04.md" in (
        PROJECT_ROOT / "docs" / "08-References" / "business" / "master-plan-checklist.md"
    ).read_text(encoding="utf-8")


def test_competitive_reassessment_keeps_cos_wedge_clear() -> None:
    text = DOC.read_text(encoding="utf-8")

    required = [
        "Cognitive OS should not copy OpenClaw or Hermes Agent.",
        "operational layer for engineering agents",
        "governance, verification, and portability discipline",
        "The competitive wedge is therefore:",
        "easier to trust, easier to verify, and harder to outgrow",
    ]

    for phrase in required:
        assert phrase in text


def test_competitive_reassessment_tracks_evidence_and_uncertainty() -> None:
    text = DOC.read_text(encoding="utf-8")

    for phrase in [
        "Source Status",
        "Confidence",
        "OpenRouter app rankings",
        "OpenClaw GitHub",
        "Hermes Agent GitHub",
        "ClawHub self-improvement example",
        "Avoid hardcoding exact numbers",
    ]:
        assert phrase in text


def test_competitive_reassessment_turns_gaps_into_provable_work() -> None:
    text = DOC.read_text(encoding="utf-8")

    for phrase in [
        "Native Governed Self-Improvement Mode",
        "Skill Lifecycle Autopilot",
        "Memory/Profile Bootstrap",
        "One-Command Local and Headless Proof Path",
        "Curated Workflow/Package Proofs",
        "Proof Required",
        "Contract test for draft -> approve -> project -> discover",
    ]:
        assert phrase in text


def test_competitive_reassessment_roadmap_prioritizes_provable_work() -> None:
    rows = _table_rows(DOC.read_text(encoding="utf-8"), "## Roadmap Addendum")
    work_by_priority = [(row[0], row[1], row[2]) for row in rows[1:]]

    assert work_by_priority[:5] == [
        ("P0", "Document and enforce governed self-improvement contract.", "Contract test for draft -> approve -> project -> discover."),
        ("P0", "Add competitive benchmark fixture for Hermes/OpenClaw-style learning loops.", "Runtime comparison report with vanilla vs COS outcomes."),
        ("P1", "Add `cos skill suggest/draft/promote` or equivalent scripts.", "Unit + integration tests, no direct writes outside canonical state."),
        ("P1", "Add memory/profile bootstrap proof.", "Codex and Claude doctors prove save/recover/profile without driver lock-in."),
        ("P1", "Add local headless `cos run-task` proof fixture.", "Patch + tests + gates + summary artifact."),
    ]
