# SCOPE: os-only
"""Behavior tests for lib.domain_model (ADR-054 Phase 2).

Real filesystem via tmp_path. No mocks.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


from lib.domain_model import (
    DomainModelScaffolder,
    FOOTER_MARKER,
    HEADER_MARKER,
    render_template,
)


def test_render_template_contains_required_sections():
    body = render_template("Acme", "b2b saas")
    for heading in [
        "## Bounded Contexts",
        "## Core Entities",
        "## Ubiquitous Language",
        "## Domain Events",
    ]:
        assert heading in body, f"missing heading {heading}"
    assert "Acme" in body
    assert "b2b saas" in body
    assert HEADER_MARKER in body
    assert FOOTER_MARKER in body
    assert "<!-- TODO -->" in body


def test_scaffold_creates_file_in_right_location(tmp_path: Path):
    s = DomainModelScaffolder(project_dir=tmp_path, brief="ecommerce")
    result = s.scaffold()
    expected = tmp_path / "docs" / "03-domain-risk" / "domain-model.md"
    assert result.action == "created"
    assert result.path == expected
    assert expected.exists()
    assert "ecommerce" in expected.read_text()


def test_idempotent_preserves_user_tail_content(tmp_path: Path):
    s = DomainModelScaffolder(project_dir=tmp_path, brief="first")
    s.scaffold()
    target = tmp_path / "docs" / "03-domain-risk" / "domain-model.md"

    # User adds content below the footer marker
    current = target.read_text()
    user_addendum = "\n## MY NOTES\n\nhand-written content that must survive\n"
    target.write_text(current + user_addendum)
    assert "hand-written content" in target.read_text()

    # Re-run — autogen block is refreshed, user tail preserved
    s2 = DomainModelScaffolder(project_dir=tmp_path, brief="second")
    result = s2.scaffold()
    assert result.action == "extended"
    new_text = target.read_text()
    assert "hand-written content" in new_text
    assert "second" in new_text
    assert "first" not in new_text  # autogen block was replaced


def test_skips_existing_file_without_markers(tmp_path: Path):
    target = tmp_path / "docs" / "03-domain-risk" / "domain-model.md"
    target.parent.mkdir(parents=True)
    target.write_text("# User-authored, no markers\n\nImportant content.\n")

    s = DomainModelScaffolder(project_dir=tmp_path, brief="ignored")
    result = s.scaffold()
    assert result.action == "skipped"
    # Content untouched
    assert "User-authored" in target.read_text()
    assert "Bounded Contexts" not in target.read_text()


def test_overwrite_replaces_everything(tmp_path: Path):
    target = tmp_path / "docs" / "03-domain-risk" / "domain-model.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Old content\n")

    s = DomainModelScaffolder(project_dir=tmp_path, brief="fresh", overwrite=True)
    result = s.scaffold()
    assert result.action == "overwritten"
    body = target.read_text()
    assert "Old content" not in body
    assert "Bounded Contexts" in body
    assert "fresh" in body


def test_empty_brief_injects_todo_placeholder(tmp_path: Path):
    s = DomainModelScaffolder(project_dir=tmp_path, brief="")
    s.scaffold()
    body = (tmp_path / "docs" / "03-domain-risk" / "domain-model.md").read_text()
    assert "TODO: describe domain" in body


def test_cli_end_to_end(tmp_path: Path):
    script = Path(__file__).resolve().parents[2] / "scripts" / "domain_model.py"
    assert script.exists()
    result = subprocess.run(
        [sys.executable, str(script),
         "--project-dir", str(tmp_path / "cli"),
         "--brief", "simple ecommerce",
         "--json"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["action"] == "created"
    assert (tmp_path / "cli" / "docs" / "03-domain-risk" / "domain-model.md").exists()
