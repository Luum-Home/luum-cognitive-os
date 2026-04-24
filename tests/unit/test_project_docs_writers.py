# SCOPE: both
"""Behavior tests for ADR-054/055 docs writers.

Covers:
    - lib.docs_writer primitives (slugify, resolve_category_dir, write_doc)
    - scripts/security_audit_writer.py (CLI, via subprocess)
    - scripts/rules_export.py (CLI, via subprocess)
    - hooks/project-docs-convention.sh (soft-warn + strict modes)

Real filesystem (tmp_path). No mocks. UV runs the subprocesses so
package imports (`lib.docs_writer`) resolve the same way agents do.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from lib.docs_writer import (
    CATEGORY_DIR_NAMES,
    resolve_category_dir,
    slugify,
    write_doc,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# 1. lib.docs_writer primitives
# ---------------------------------------------------------------------------


def test_category_names_match_scaffolder_contract():
    from lib.project_scaffolder import CATEGORIES

    scaffolder_names = tuple(name for name, _, _ in CATEGORIES)
    assert CATEGORY_DIR_NAMES == scaffolder_names, (
        "docs_writer.CATEGORY_DIR_NAMES must mirror project_scaffolder.CATEGORIES "
        "so writers stay in sync with the ADR-054 contract."
    )


def test_slugify_basic():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("   spaces   ") == "spaces"
    assert slugify("already-ok") == "already-ok"
    assert slugify("Multiple   Spaces & Symbols!!") == "multiple-spaces-symbols"


def test_slugify_handles_empty_fallback():
    assert slugify("") == "report"
    assert slugify("!!!") == "report"


def test_resolve_category_dir_creates_missing(tmp_path):
    out = resolve_category_dir(tmp_path, "04-seguridad")
    assert out == tmp_path / "docs" / "04-seguridad"
    assert out.is_dir()


def test_resolve_category_dir_rejects_unknown(tmp_path):
    with pytest.raises(ValueError, match="unknown category"):
        resolve_category_dir(tmp_path, "99-invented")


def test_write_doc_creates_file_with_timestamped_name(tmp_path):
    ts = datetime(2026, 4, 21, 18, 30, 45)
    out = write_doc(tmp_path, "04-seguridad", "my audit", "body", timestamp=ts)
    assert out.exists()
    assert out.name == "my-audit-2026-04-21-183045.md"
    assert out.read_text() == "body"
    assert out.parent == tmp_path / "docs" / "04-seguridad"


def test_write_doc_respects_filename_override(tmp_path):
    out = write_doc(tmp_path, "08-estandares", "ignored", "hello", filename="custom.md")
    assert out.name == "custom.md"
    assert out.read_text() == "hello"


def test_write_doc_rejects_unknown_category(tmp_path):
    with pytest.raises(ValueError):
        write_doc(tmp_path, "99-bogus", "x", "y")


# ---------------------------------------------------------------------------
# 2. security-audit-writer CLI
# ---------------------------------------------------------------------------


def _run_py_script(script_rel: str, args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(REPO_ROOT / script_rel)] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=stdin,
        cwd=REPO_ROOT,
        check=False,
    )


def test_security_audit_writer_writes_from_file(tmp_path):
    report = tmp_path / "audit.md"
    report.write_text("# Security Audit Report\n\nAll clean.\n")
    proj = tmp_path / "proj"

    result = _run_py_script(
        "scripts/security_audit_writer.py",
        ["--project-dir", str(proj), "--report-file", str(report), "--json"],
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    written = Path(payload["written"])
    assert written.exists()
    assert written.parent == proj / "docs" / "04-seguridad"
    assert "Security Audit Report" in written.read_text()


def test_security_audit_writer_reads_stdin(tmp_path):
    proj = tmp_path / "proj"
    body = "# From stdin\n\nNothing critical.\n"
    result = _run_py_script(
        "scripts/security_audit_writer.py",
        ["--project-dir", str(proj), "--slug", "initial"],
        stdin=body,
    )
    assert result.returncode == 0, result.stderr
    files = list((proj / "docs" / "04-seguridad").glob("initial-*.md"))
    assert len(files) == 1
    assert files[0].read_text() == body


def test_security_audit_writer_rejects_empty_stdin(tmp_path):
    proj = tmp_path / "proj"
    result = _run_py_script(
        "scripts/security_audit_writer.py",
        ["--project-dir", str(proj)],
        stdin="",
    )
    assert result.returncode == 1
    assert "empty" in result.stderr.lower()


# ---------------------------------------------------------------------------
# 3. rules-export CLI
# ---------------------------------------------------------------------------


def test_rules_export_default_set(tmp_path):
    proj = tmp_path / "adopter"
    result = _run_py_script(
        "scripts/rules_export.py",
        ["--project-dir", str(proj), "--json"],
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    out_path = Path(payload["written"])
    assert out_path.exists()
    assert out_path.parent == proj / "docs" / "08-estandares"
    body = out_path.read_text()
    assert "Rules Snapshot" in body
    # At least the 6 defaults are present as section headers.
    for name in ("so-slo", "definition-of-done", "credential-management"):
        assert f"## {name}" in body, f"missing rule section: {name}"


def test_rules_export_custom_subset(tmp_path):
    proj = tmp_path / "adopter"
    result = _run_py_script(
        "scripts/rules_export.py",
        ["--project-dir", str(proj), "--rules", "so-slo", "responsiveness", "--json"],
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["rules_count"] == 2
    body = Path(payload["written"]).read_text()
    assert "## so-slo" in body
    assert "## responsiveness" in body
    assert "## definition-of-done" not in body  # excluded


def test_rules_export_rejects_unknown_rule(tmp_path):
    proj = tmp_path / "adopter"
    result = _run_py_script(
        "scripts/rules_export.py",
        ["--project-dir", str(proj), "--rules", "this-does-not-exist"],
    )
    assert result.returncode == 1
    assert "not found" in result.stderr.lower()


# ---------------------------------------------------------------------------
# 4. project-docs-convention.sh hook
# ---------------------------------------------------------------------------


def _run_hook(args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(REPO_ROOT / "hooks/project-docs-convention.sh")] + args,
        capture_output=True,
        text=True,
        input=stdin,
        check=False,
    )


def test_hook_warns_when_docs_missing(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    result = _run_hook(["--project-dir", str(empty)])
    assert result.returncode == 0  # soft-warn
    assert "WARNING" in result.stderr or "missing" in result.stderr.lower()


def test_hook_strict_fails_when_docs_missing(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    result = _run_hook(["--project-dir", str(empty), "--strict"])
    assert result.returncode == 2


def test_hook_passes_when_all_categories_present(tmp_path):
    proj = tmp_path / "ok"
    (proj / "docs").mkdir(parents=True)
    for cat in CATEGORY_DIR_NAMES:
        (proj / "docs" / cat).mkdir()
    result = _run_hook(["--project-dir", str(proj)])
    assert result.returncode == 0
    assert "OK" in result.stdout or result.stderr == ""


def test_hook_json_output_shape(tmp_path):
    proj = tmp_path / "partial"
    (proj / "docs" / "01-contexto").mkdir(parents=True)
    result = _run_hook(["--project-dir", str(proj), "--json"])
    assert result.returncode == 0
    payload = json.loads(result.stdout.strip())
    assert payload["status"] == "violation"
    assert payload["present_count"] == 1
    assert payload["missing_count"] == 9
    assert "02-arquitectura" in payload["missing"]


# ---------------------------------------------------------------------------
# 5. End-to-end: scaffolder + writers compose cleanly
# ---------------------------------------------------------------------------


def test_scaffold_then_write_audit_composes(tmp_path):
    """Full chain: scaffold a project, then write an audit report into it."""
    from lib.project_scaffolder import ProjectScaffolder

    proj = tmp_path / "composed"
    ProjectScaffolder(project_name="Composed", project_dir=proj).scaffold_all()

    # Now write a report. The 04-seguridad dir already exists.
    out = write_doc(proj, "04-seguridad", "test-report", "# Test\n")
    assert out.exists()
    assert out.parent == proj / "docs" / "04-seguridad"

    # Hook should now be green.
    result = _run_hook(["--project-dir", str(proj)])
    assert result.returncode == 0
