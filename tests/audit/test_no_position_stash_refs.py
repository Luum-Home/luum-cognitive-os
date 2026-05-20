from __future__ import annotations

from pathlib import Path

from scripts.stash_quarantine_audit import audit


def test_no_non_forensic_positional_stash_refs_in_operator_docs(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "guide.md"
    doc.parent.mkdir()
    doc.write_text("Use the reviewed stash SHA as durable identity.\n", encoding="utf-8")

    assert audit(tmp_path, ["docs/guide.md"]) == []


def test_positional_stash_refs_are_flagged_when_present_in_guidance(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "guide.md"
    doc.parent.mkdir()
    doc.write_text("Restore later with stash@{0}.\n", encoding="utf-8")

    findings = audit(tmp_path, ["docs/guide.md"])

    assert any(item.code == "positional-stash-reference" for item in findings)
