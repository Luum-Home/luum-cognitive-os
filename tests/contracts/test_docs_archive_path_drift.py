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
        "docs/archive/old.md",
        "docs/reports/report.md",
        "docs/archived/legacy.md",
    ):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# doc\n", encoding="utf-8")

    candidates = {p.relative_to(tmp_path).as_posix() for p in docs_execution_audit.candidate_docs(tmp_path)}

    assert "README.md" in candidates
    assert "AGENTS.md" in candidates
    assert "docs/active.md" in candidates
    assert "docs/archive/old.md" not in candidates
    assert "docs/reports/report.md" not in candidates
    assert "docs/archived/legacy.md" in candidates


def test_routing_docs_no_longer_reference_legacy_archived_path() -> None:
    routing_text = (REPO_ROOT / "docs" / "AGENTS.md").read_text(encoding="utf-8")
    audit_text = (REPO_ROOT / "scripts" / "docs_execution_audit.py").read_text(encoding="utf-8")

    assert "docs/archive/" in routing_text
    assert "docs/archived/" not in routing_text
    assert '"docs/archive/"' in audit_text
    assert '"docs/archived/"' not in audit_text
