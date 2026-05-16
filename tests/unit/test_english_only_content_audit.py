from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path


from scripts.english_only_content_audit import (
    audit,
    first_forbidden_script_letter,
    report_to_markdown,
)


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


def _short_non_english_sample() -> str:
    return _utf8("4e6563657369746f20766572206573746f2e")


def _non_english_frontmatter() -> str:
    return _utf8(
        "74c3ad74756c6f3a20616ec3a16c6973697320646520636f6d706f6e656e7465735c6e"
        "66656368613a20323032362d30352d31365c6e"
        "6574697175657461733a205b726576697369c3b36e2c206172717569746563747572615d"
    )


def _non_english_docstring() -> str:
    return _utf8(
        "50726f6365736172206c6120636f6c6120646520656c656d656e746f7320656e7472616e7465732e20"
        "457374612066756e6369c3b36e20736520656e63617267612064652072657669736172206361646120"
        "656c656d656e746f20792061706c69636172206c61207472616e73666f726d616369c3b36e206e656365736172696120"
        "616e74657320646520656e766961726c6f20616c206dc3b364756c6f2064652073616c6964612e20"
        "5265746f726e61206c61206c6973746120646520656c656d656e746f732070726f63657361646f732e"
    )


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "add", "."], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


# ---------------------------------------------------------------------------
# Fast pre-pass tests (no lingua required)
# ---------------------------------------------------------------------------

def test_first_forbidden_script_letter_flags_cyrillic() -> None:
    assert first_forbidden_script_letter(chr(0x0416) + " signal") == chr(0x0416)


def test_first_forbidden_script_letter_allows_latin_diacritic() -> None:
    assert first_forbidden_script_letter("Mat" + chr(0x00ED) + "as") is None


def test_first_forbidden_script_letter_flags_greek_letter() -> None:
    assert first_forbidden_script_letter("score = " + chr(0x03B1)) == chr(0x03B1)


def test_first_forbidden_script_letter_allows_micro_sign() -> None:
    assert first_forbidden_script_letter("limit = 5" + chr(0x00B5) + "s") is None


def test_audit_non_latin_script_flagged(tmp_path: Path) -> None:
    """Non-Latin script (e.g. Cyrillic) triggers the pre-pass regardless of lingua."""
    (tmp_path / "note.md").write_text(chr(0x0416) + " signal\n", encoding="utf-8")
    _git_init(tmp_path)
    report = audit(tmp_path)
    assert report.finding_count >= 1
    assert report.findings[0].code == "non-english-script"


def test_audit_forbidden_punctuation_flagged(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text(chr(0x00BF) + "Really?\n", encoding="utf-8")
    _git_init(tmp_path)
    report = audit(tmp_path)
    assert report.finding_count >= 1
    assert report.findings[0].code == "non-english-punctuation"


# ---------------------------------------------------------------------------
# Lingua paragraph-level detection
# ---------------------------------------------------------------------------

def test_pure_english_paragraph_no_finding(tmp_path: Path) -> None:
    text = textwrap.dedent("""\
        # Architecture Overview

        This module implements the primary routing layer for the agent orchestration
        system. It dispatches incoming requests to registered skill handlers based
        on a confidence threshold determined by the semantic matcher component.
        All handlers must implement the standard interface defined in the base class.
    """)
    (tmp_path / "arch.md").write_text(text, encoding="utf-8")
    _git_init(tmp_path)
    report = audit(tmp_path, min_confidence=0.85)
    non_english = [f for f in report.findings if f.code == "non-english-paragraph"]
    assert non_english == [], f"Unexpected findings: {non_english}"


def test_pure_non_english_paragraph_flagged(tmp_path: Path) -> None:
    text = textwrap.dedent(f"""\
        # Analysis

        {_non_english_sample()}
    """)
    (tmp_path / "note.md").write_text(text, encoding="utf-8")
    _git_init(tmp_path)
    report = audit(tmp_path, min_confidence=0.85)
    non_english = [f for f in report.findings if f.code == "non-english-paragraph"]
    assert len(non_english) >= 1, f"Expected a non-English finding; got: {report.findings}"


def test_mixed_language_paragraph_flagged(tmp_path: Path) -> None:
    text = textwrap.dedent(f"""\
        # Assessment

        EXTERNAL_BETTER (in its domain). {_non_english_sample()}
    """)
    (tmp_path / "note.md").write_text(text, encoding="utf-8")
    _git_init(tmp_path)
    report = audit(tmp_path, min_confidence=0.70)
    non_english = [f for f in report.findings if f.code in ("non-english-paragraph", "weak-english")]
    assert len(non_english) >= 1, f"Expected mixed-language finding; got: {report.findings}"


def test_short_paragraph_below_min_words_skipped(tmp_path: Path) -> None:
    # 5-word non-English phrase — below default min_words=15.
    text = f"# Title\n\n{_short_non_english_sample()}\n"
    (tmp_path / "note.md").write_text(text, encoding="utf-8")
    _git_init(tmp_path)
    report = audit(tmp_path, min_words=15)
    non_english = [f for f in report.findings if f.code == "non-english-paragraph"]
    assert non_english == [], f"Short phrase should not trigger lingua: {non_english}"


def test_code_fence_inside_markdown_skipped(tmp_path: Path) -> None:
    text = textwrap.dedent(f"""\
        # Example

        This section shows a fixture used in testing.

        ```
        {_non_english_sample()}
        ```

        The code above is an example only.
    """)
    (tmp_path / "note.md").write_text(text, encoding="utf-8")
    _git_init(tmp_path)
    report = audit(tmp_path, min_confidence=0.85)
    non_english = [f for f in report.findings if f.code == "non-english-paragraph"]
    assert non_english == [], f"Content inside code fence should not flag: {non_english}"


def test_yaml_frontmatter_skipped(tmp_path: Path) -> None:
    text = textwrap.dedent(f"""\
        ---
        {_non_english_frontmatter()}
        ---

        # Overview

        This document describes the component architecture for the routing module.
        All components are implemented following the standard interface pattern
        defined in the base class for consistent behavior across the system.
    """)
    (tmp_path / "note.md").write_text(text, encoding="utf-8")
    _git_init(tmp_path)
    report = audit(tmp_path, min_confidence=0.85)
    non_english = [f for f in report.findings if f.code == "non-english-paragraph"]
    assert non_english == [], f"Frontmatter should be stripped: {non_english}"


# ---------------------------------------------------------------------------
# Allow-marker suppression
# ---------------------------------------------------------------------------

def test_allow_marker_within_3_lines_suppresses(tmp_path: Path) -> None:
    text = textwrap.dedent(f"""\
        # Test fixtures

        <!-- english-only-content-audit: allow -->
        {_non_english_sample()}
    """)
    (tmp_path / "fixture.md").write_text(text, encoding="utf-8")
    _git_init(tmp_path)
    report = audit(tmp_path, min_confidence=0.85)
    non_english = [f for f in report.findings if f.code == "non-english-paragraph"]
    assert non_english == [], f"Allow marker should suppress finding: {non_english}"


def test_allow_block_marker_suppresses_entire_paragraph(tmp_path: Path) -> None:
    text = textwrap.dedent(f"""\
        # Protocol doc

        <!-- english-only-content-audit: allow-block -->
        {_non_english_sample()}
    """)
    (tmp_path / "proto.md").write_text(text, encoding="utf-8")
    _git_init(tmp_path)
    report = audit(tmp_path, min_confidence=0.85)
    non_english = [f for f in report.findings if f.code == "non-english-paragraph"]
    assert non_english == [], f"allow-block marker should suppress: {non_english}"


# ---------------------------------------------------------------------------
# Tree-sitter source code detection
# ---------------------------------------------------------------------------

def test_python_docstring_non_english_flagged(tmp_path: Path) -> None:
    code = textwrap.dedent(f'''\
        def process_queue(items):
            """{_non_english_docstring()}"""
            return [transform(item) for item in items]
    ''')
    (tmp_path / "processor.py").write_text(code, encoding="utf-8")
    _git_init(tmp_path)
    report = audit(tmp_path, min_confidence=0.80)
    non_english = [f for f in report.findings if f.code == "non-english-paragraph"]
    assert len(non_english) >= 1, f"non-English docstring should be flagged: {report.findings}"
    # Finding should point to the docstring line, not identifiers.
    assert non_english[0].line >= 2


def test_python_english_identifiers_no_finding(tmp_path: Path) -> None:
    code = textwrap.dedent('''\
        def compute_price(amount: int) -> int:
            """Compute final price."""
            return amount
    ''')
    (tmp_path / "pricing.py").write_text(code, encoding="utf-8")
    _git_init(tmp_path)
    report = audit(tmp_path, min_confidence=0.85)
    non_english = [f for f in report.findings if f.code == "non-english-paragraph"]
    assert non_english == [], (
        f"English identifiers should not be flagged: {non_english}"
    )


# ---------------------------------------------------------------------------
# Markdown report format
# ---------------------------------------------------------------------------

def test_markdown_report_lists_findings(tmp_path: Path) -> None:
    (tmp_path / "sample.md").write_text(chr(0x0416) + " signal\n", encoding="utf-8")
    _git_init(tmp_path)
    markdown = report_to_markdown(audit(tmp_path))
    assert "English-only Content Audit" in markdown
    assert "`sample.md:1`" in markdown
    assert "non-english-script" in markdown


def test_audit_scans_git_tracked_files_and_reports_locations(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "note.md").write_text(
        "# Note\n" + chr(0x0416) + " signal\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("# English only\n", encoding="utf-8")
    _git_init(tmp_path)
    report = audit(tmp_path)
    assert report.scanned_files == 2
    assert report.finding_count >= 1
    cyrillic_findings = [f for f in report.findings if f.code == "non-english-script"]
    assert any(f.file == "docs/note.md" for f in cyrillic_findings)
