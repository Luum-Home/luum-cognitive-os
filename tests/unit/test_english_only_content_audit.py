from __future__ import annotations

import base64
import subprocess
from pathlib import Path

from scripts.english_only_content_audit import audit, classify_line, report_to_markdown


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "add", "."], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _decoded(value: str) -> str:
    return base64.b64decode(value).decode("utf-8")


def test_classify_line_flags_encoded_forbidden_term() -> None:
    text = _decoded("bmVjZXNpdG8=") + " action"

    assert classify_line(text) == ("non-english-term", "error", _decoded("bmVjZXNpdG8="))


def test_classify_line_flags_non_english_script() -> None:
    assert classify_line(chr(0x0416) + " signal") == ("non-english-script", "error", chr(0x0416))


def test_classify_line_flags_forbidden_punctuation() -> None:
    assert classify_line(chr(0x00BF) + "Can this happen?") == (
        "non-english-punctuation",
        "error",
        chr(0x00BF),
    )


def test_classify_line_flags_latin_diacritic() -> None:
    assert classify_line("Author: Mat" + chr(0x00ED) + "as") == ("non-ascii-letter", "error", chr(0x00ED))


def test_audit_scans_git_tracked_files_and_reports_locations(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "note.md").write_text("# Note\n" + _decoded("bmVjZXNpdG8=") + " action.\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# English only\n", encoding="utf-8")
    _git_init(tmp_path)

    report = audit(tmp_path)

    assert report.scanned_files == 2
    assert report.finding_count == 1
    assert report.findings[0].file == "docs/note.md"
    assert report.findings[0].line == 2
    assert report.findings[0].code == "non-english-term"


def test_audit_respects_allow_marker(tmp_path: Path) -> None:
    (tmp_path / "fixture.md").write_text(
        "<!-- english-only-content-audit: allow -->\n"
        "Fixture keeps the literal " + chr(0x00BF) + " for parser coverage.\n",
        encoding="utf-8",
    )
    _git_init(tmp_path)

    report = audit(tmp_path)

    assert report.findings == ()


def test_markdown_report_lists_findings(tmp_path: Path) -> None:
    (tmp_path / "sample.md").write_text(chr(0x0416) + " signal\n", encoding="utf-8")
    _git_init(tmp_path)

    markdown = report_to_markdown(audit(tmp_path))

    assert "English-only Content Audit" in markdown
    assert "`sample.md:1`" in markdown
    assert "non-english-script" in markdown
