"""Unit tests for lib/confidentiality_scanner.py

Tests cover external-path detection, attribution-phrase detection, repo URL
detection, protected-term detection, and the is_scannable_path helper.

Python 3.9+ compatible.
"""

import pytest

from lib.confidentiality_scanner import (
    ProtectedTerms,
    Violation,
    is_scannable_path,
    scan_file,
    scan_text,
)

pytestmark = [pytest.mark.unit, pytest.mark.behavior]


# ---------------------------------------------------------------------------
# A1 — External project path is detected
# ---------------------------------------------------------------------------


def test_detects_external_project_path():
    """A path from a different project triggers an external_path violation."""
    text = (
        "The auth module at /Users/matias/Projects/otro-proyecto/src/auth.go"
        " was used as reference."
    )
    current = "/Users/matias/Projects/mi-proyecto"
    violations = scan_text(text, current_project_dir=current)

    ext = [v for v in violations if v.pattern_type == "external_path"]
    assert len(ext) == 1
    assert "otro-proyecto" in ext[0].matched_text


# ---------------------------------------------------------------------------
# A2 — Same-project path is allowed
# ---------------------------------------------------------------------------


def test_ignores_same_project_path():
    """A path that belongs to the current project must not be flagged."""
    text = (
        "See /Users/matias/Projects/mi-proyecto/docs/README.md for details."
    )
    current = "/Users/matias/Projects/mi-proyecto"
    violations = scan_text(text, current_project_dir=current)

    ext = [v for v in violations if v.pattern_type == "external_path"]
    assert ext == []


# ---------------------------------------------------------------------------
# A3 — Protected repo URL is detected
# ---------------------------------------------------------------------------


def test_detects_protected_repo_url():
    """A github.com URL whose org is in the protected list triggers a repo_url violation."""
    text = "The code was adapted from github.com/luum/repo-privado implementation."
    terms = ProtectedTerms(org_names=["luum"])
    violations = scan_text(text, terms=terms)

    repo = [v for v in violations if v.pattern_type == "repo_url"]
    assert len(repo) == 1
    assert "luum" in repo[0].matched_text


# ---------------------------------------------------------------------------
# B1 — Spanish attribution with protected project name
# ---------------------------------------------------------------------------


def test_detects_spanish_attribution_with_protected_term():
    """A Spanish attribution phrase followed by a protected project name is caught."""
    text = "El diseño está basado en el modelo de project-alpha para facilitar la integración."
    terms = ProtectedTerms(project_names=["project-alpha"])
    violations = scan_text(text, terms=terms)

    attr = [v for v in violations if v.pattern_type == "attribution_phrase"]
    assert len(attr) >= 1
    assert "project-alpha" in attr[0].matched_text


# ---------------------------------------------------------------------------
# B2 — English attribution with external path
# ---------------------------------------------------------------------------


def test_detects_english_attribution_with_external_path():
    """An English attribution phrase followed by an external path is flagged."""
    text = "This handler was adapted from the auth module in /Users/matias/Projects/otro/."
    current = "/Users/matias/Projects/mine"
    violations = scan_text(text, current_project_dir=current)

    # Either attribution_phrase or external_path (or both) must fire.
    assert len(violations) >= 1
    types = {v.pattern_type for v in violations}
    assert types & {"attribution_phrase", "external_path"}


# ---------------------------------------------------------------------------
# B3 — Clean text produces no violations
# ---------------------------------------------------------------------------


def test_no_violations_in_clean_text():
    """Generic architectural prose without identifiers produces zero violations."""
    text = "We use a microservices architecture with event sourcing and CQRS."
    violations = scan_text(text)
    assert violations == []


# ---------------------------------------------------------------------------
# B4 — is_scannable_path classification
# ---------------------------------------------------------------------------


def test_is_scannable_path():
    """Verify correct classification of scannable vs non-scannable paths."""
    # Scannable
    assert is_scannable_path("docs/resumen-ejecutivo.md") is True
    assert is_scannable_path("README.md") is True
    assert is_scannable_path("docs/01-contexto/brief.md") is True
    assert is_scannable_path("CHANGELOG.md") is True
    assert is_scannable_path("README") is True
    # Path containing /docs/ but no .md extension
    assert is_scannable_path("/project/docs/overview.rst") is True

    # Not scannable
    assert is_scannable_path("src/main.go") is False
    assert is_scannable_path("tests/test_foo.py") is False
    assert is_scannable_path("go.mod") is False
    assert is_scannable_path("lib/scanner.py") is False
    assert is_scannable_path("hooks/rate-limiter.sh") is False


# ---------------------------------------------------------------------------
# Extra: scan_file sets correct line numbers
# ---------------------------------------------------------------------------


def test_scan_file_reports_correct_line_numbers(tmp_path):
    """scan_file should report the 1-based line number of each violation."""
    content = (
        "Line 1: all good.\n"
        "Line 2: see /Users/other/Projects/secret/auth.go for reference.\n"
        "Line 3: nothing here.\n"
    )
    doc = tmp_path / "test.md"
    doc.write_text(content, encoding="utf-8")

    current = "/Users/other/Projects/mine"
    violations = scan_file(str(doc), current_project_dir=current)

    ext = [v for v in violations if v.pattern_type == "external_path"]
    assert len(ext) == 1
    assert ext[0].line_number == 2
