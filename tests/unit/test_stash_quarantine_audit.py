from __future__ import annotations

from pathlib import Path

from scripts.stash_quarantine_audit import audit


def test_audit_flags_bare_stash_pop_and_positional_refs(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "recover.md"
    doc.parent.mkdir()
    doc.write_text("Restore with git stash pop\nUse stash@{0} later\n", encoding="utf-8")

    findings = audit(tmp_path, ["docs/recover.md"])

    codes = {item.code for item in findings}
    assert "bare-stash-operation" in codes
    assert "positional-stash-reference" in codes


def test_audit_allows_reviewed_apply_target(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "recover.md"
    doc.parent.mkdir()
    doc.write_text("Inspect first, then git stash apply <reviewed-stash-ref>\n", encoding="utf-8")

    findings = audit(tmp_path, ["docs/recover.md"])

    assert findings == []
