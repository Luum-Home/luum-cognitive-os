from __future__ import annotations

from pathlib import Path

from scripts.stash_quarantine_audit import audit


def test_bare_stash_apply_is_flagged_in_os_guidance(tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "restore.sh"
    script.parent.mkdir()
    script.write_text("git stash apply\n", encoding="utf-8")

    findings = audit(tmp_path, ["scripts/restore.sh"])

    assert any(item.code == "bare-stash-operation" for item in findings)


def test_reviewed_stash_apply_target_is_allowed(tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "restore.sh"
    script.parent.mkdir()
    script.write_text("git stash apply <reviewed-stash-ref-or-sha>\n", encoding="utf-8")

    assert audit(tmp_path, ["scripts/restore.sh"]) == []
