"""Audit canonical SDD Engram topic-key namespace."""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.audit

REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL = "planning/{change-name}/"
LEGACY_ALLOWED = {
    "rules/engram-organization.md",
    "rules/context-optimization.md",
    "docs/reports/dx-assessment-2026-05-02.md",
    "docs/reports/docs-execution-latest.md",
    "docs/reports/docs-execution-latest.json",
    "docs/adrs/ADR-029.md",
    "docs/adrs/ADR-128-data-layer-integrity-fixes.md",
    # MOC referencing legacy sdd/{change}/{phase} key format for human navigation
    "docs/00-MOCs/workflow.md",
}
SCAN_ROOTS = ("skills", "docs", "rules")
LEGACY_PATTERNS = ("sdd/{change-name}/", "sdd/{change}/")


def _candidate_files() -> list[Path]:
    files: list[Path] = []
    for root_name in SCAN_ROOTS:
        root = REPO_ROOT / root_name
        files.extend(path for path in root.rglob("*") if path.suffix in {".md", ".json"})
    return files


def test_sdd_docs_use_planning_topic_namespace() -> None:
    offenders: list[str] = []
    for path in _candidate_files():
        rel = str(path.relative_to(REPO_ROOT))
        if rel in LEGACY_ALLOWED:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern in text for pattern in LEGACY_PATTERNS):
            offenders.append(rel)
    assert offenders == []


def test_sdd_continue_documents_canonical_namespace() -> None:
    text = (REPO_ROOT / "skills" / "sdd-continue" / "SKILL.md").read_text(encoding="utf-8")
    assert CANONICAL in text
