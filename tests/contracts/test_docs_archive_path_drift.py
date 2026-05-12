"""Regression coverage for docs archive path drift."""

from __future__ import annotations

from pathlib import Path

from scripts import docs_execution_audit

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_docs_execution_audit_excludes_current_archive_not_legacy_archived(tmp_path: Path) -> None:
    for rel in (
        "README.md",
        "AGENTS.md",
        "docs/active.md",
        "docs/99-Archive/archive/old.md",
        "docs/06-Daily/reports/report.md",
        "docs/99-Archive/archived/legacy.md",
    ):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# doc\n", encoding="utf-8")

    candidates = {p.relative_to(tmp_path).as_posix() for p in docs_execution_audit.candidate_docs(tmp_path)}

    assert "README.md" in candidates
    assert "AGENTS.md" in candidates
    assert "docs/active.md" in candidates
    assert "docs/99-Archive/archive/old.md" not in candidates
    assert "docs/06-Daily/reports/report.md" not in candidates
    assert "docs/99-Archive/archived/legacy.md" in candidates


def test_routing_docs_no_longer_reference_legacy_archived_path() -> None:
    routing_text = (REPO_ROOT / "docs" / "00-MOCs" / "entrypoints" / "AGENTS.md").read_text(encoding="utf-8")
    audit_text = (REPO_ROOT / "scripts" / "docs_execution_audit.py").read_text(encoding="utf-8")

    assert "docs/99-Archive/archive/" in routing_text
    assert "docs/99-Archive/archived/" not in routing_text
    assert '"docs/99-Archive/archive/"' in audit_text
    assert '"docs/99-Archive/archived/"' not in audit_text
