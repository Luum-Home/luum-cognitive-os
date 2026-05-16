"""Regression tests for repository-wide English-only content auditing.

The fixtures synthesize non-English text at runtime so this test module remains
English-only while still exercising detection paths.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.english_only_content_audit import audit, scan_file


def _utf8(hex_text: str) -> str:
    return bytes.fromhex(hex_text).decode("utf-8")


def _non_english_sample() -> str:
    return _utf8(
        "4573667565727a6f3a20332d352064c3ad6173207061726120656c207072696d657220736b696c6c20"
        "70696c6f746f2e204e6f2074656e656d6f73206f7074696d697a65722064652070726f6d7074732e20"
        "4c61207461626c6120617578696c69617220646520706174726f6e6573206e6f20726571756965726520"
        "4b47206e7565766f2e20456c206dc3b364756c6f2064652064657465636369c3b36e20736520707565646520"
        "72657574696c697a617220646972656374616d656e746520656e20656c20706970656c696e65206578697374656e74652e20"
        "4e656365736974616d6f732072657669736172206c6120636f6e6669677572616369c3b36e20616e74657320"
        "64652070726f636564657220636f6e20656c20646573706c69656775652e"
    )


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "add", "."], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_scan_file_flags_dirty_fixture(tmp_path: Path) -> None:
    """A single file with non-English prose must produce a finding."""
    dirty = tmp_path / "docs" / "dirty.md"
    dirty.parent.mkdir()
    dirty.write_text("# Note\n\n" + _non_english_sample() + "\n", encoding="utf-8")
    _git_init(tmp_path)

    findings = scan_file(
        tmp_path,
        "docs/dirty.md",
        min_words=12,
        min_confidence=0.80,
    )
    assert any(
        f.code in (
            "non-english-paragraph",
            "weak-english",
            "non-english-script",
            "non-english-punctuation",
        )
        for f in findings
    ), f"Expected at least one finding; got: {findings}"


def test_audit_root_captures_all_dirty_fixtures(tmp_path: Path) -> None:
    """A root audit must flag every tracked fixture file that contains non-English prose."""
    paths = [
        tmp_path / "docs" / "dirty-a.md",
        tmp_path / "docs" / "nested" / "dirty-b.md",
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Note\n\n" + _non_english_sample() + "\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# English only\n", encoding="utf-8")
    _git_init(tmp_path)

    report = audit(
        tmp_path,
        min_words=12,
        min_confidence=0.80,
    )

    flagged_files = {f.file for f in report.findings}
    expected = {p.relative_to(tmp_path).as_posix() for p in paths}
    assert expected <= flagged_files


def test_audit_finding_count_above_zero_for_dirty_fixture(tmp_path: Path) -> None:
    """Sanity check: the detector must find more than zero issues when issues exist."""
    (tmp_path / "note.md").write_text("# Note\n\n" + _non_english_sample() + "\n", encoding="utf-8")
    _git_init(tmp_path)

    report = audit(tmp_path, min_words=12, min_confidence=0.80)
    assert report.finding_count > 0, "Detector returned zero findings for a dirty fixture."
