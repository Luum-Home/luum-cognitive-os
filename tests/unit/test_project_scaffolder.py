# SCOPE: os-only
"""Behavior tests for lib.project_scaffolder (ADR-054).

Real behavior — uses pytest's tmp_path (isolated per test, cleaned up).
No mocks. Tests verify the 10-category docs/ skeleton is created
correctly and idempotently.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lib.project_scaffolder import (
    CATEGORIES,
    ProjectScaffolder,
    expected_category_paths,
    expected_file_count,
)


EXPECTED_DIRS = [
    "01-context",
    "02-architecture",
    "03-domain-risk",
    "04-security",
    "05-features",
    "06-backoffice",
    "07-research",
    "08-standards",
    "09-execution-plan",
    "10-summaries",
]


# ---------------------------------------------------------------------------
# 1. Basic structure
# ---------------------------------------------------------------------------


def test_categories_constant_has_10_entries():
    assert len(CATEGORIES) == 10
    # Dir names are monotonically numbered 01..10
    for i, (dir_name, _, _) in enumerate(CATEGORIES, start=1):
        assert dir_name.startswith(f"{i:02d}-"), f"position {i} is {dir_name!r}"


def test_expected_file_count_is_45():
    # 10 categories × (1 README + N starter files) + 1 top-level docs/00-MOCs/entrypoints/README.md + 1 adrs/README.md = 45
    # (Extended in v1.1: added personas/roles/user-journeys/C4/glossary/rbac/prd/use-cases + adrs/ dir)
    assert expected_file_count() == 45


# ---------------------------------------------------------------------------
# 2. Scaffolding produces the expected tree
# ---------------------------------------------------------------------------


def test_scaffold_all_creates_10_category_dirs(tmp_path: Path):
    s = ProjectScaffolder(project_name="Test", project_dir=tmp_path)
    s.scaffold_all()

    for dir_name in EXPECTED_DIRS:
        cat_dir = tmp_path / "docs" / dir_name
        assert cat_dir.exists(), f"missing category dir: {dir_name}"
        assert cat_dir.is_dir()


def test_scaffold_all_creates_expected_file_count(tmp_path: Path):
    s = ProjectScaffolder(project_name="Test", project_dir=tmp_path)
    result = s.scaffold_all()

    assert len(result.created) == expected_file_count()
    assert len(result.skipped) == 0
    assert all(p.exists() and p.is_file() for p in result.created)


def test_top_level_readme_lists_all_categories(tmp_path: Path):
    s = ProjectScaffolder(project_name="Acme", project_dir=tmp_path)
    s.scaffold_all()

    readme = (tmp_path / "docs" / "README.md").read_text()
    # Project name appears in heading
    assert "Acme" in readme
    # Every category dir is linked
    for dir_name in EXPECTED_DIRS:
        assert f"{dir_name}/" in readme, f"top README doesn't link {dir_name}"


def test_every_category_has_readme(tmp_path: Path):
    s = ProjectScaffolder(project_name="Test", project_dir=tmp_path)
    s.scaffold_all()

    for dir_name in EXPECTED_DIRS:
        readme = tmp_path / "docs" / dir_name / "README.md"
        assert readme.exists(), f"{dir_name} missing README.md"
        body = readme.read_text()
        # Non-trivial content — at least a heading + category reference
        assert len(body) > 20
        assert body.startswith("# ")


# ---------------------------------------------------------------------------
# 3. The two previously-missing categories (gap fix)
# ---------------------------------------------------------------------------


def test_domain_risk_category_has_domain_model_and_risk_register(tmp_path: Path):
    s = ProjectScaffolder(project_name="T", project_dir=tmp_path)
    s.scaffold_all()

    dr = tmp_path / "docs" / "03-domain-risk"
    assert (dr / "domain-model.md").exists()
    assert (dr / "risk-register.md").exists()

    # Risk register must have a table structure (STRIDE-style)
    risk = (dr / "risk-register.md").read_text()
    assert "| Likelihood |" in risk
    assert "| Impact |" in risk

    # Domain model must mention bounded contexts + entities
    domain = (dr / "domain-model.md").read_text()
    assert "Bounded contexts" in domain
    assert "entities" in domain.lower()


def test_backoffice_category_has_ops_admin_monitoring(tmp_path: Path):
    s = ProjectScaffolder(project_name="T", project_dir=tmp_path)
    s.scaffold_all()

    bo = tmp_path / "docs" / "06-backoffice"
    assert (bo / "operations.md").exists()
    assert (bo / "admin-processes.md").exists()
    assert (bo / "monitoring.md").exists()

    ops = (bo / "operations.md").read_text()
    assert "On-call" in ops or "on-call" in ops
    assert "Rollback" in ops


# ---------------------------------------------------------------------------
# 4. Mismatch-fix categories have skill references embedded
# ---------------------------------------------------------------------------


def test_security_readme_references_security_audit_skill(tmp_path: Path):
    s = ProjectScaffolder(project_name="T", project_dir=tmp_path)
    s.scaffold_all()
    readme = (tmp_path / "docs" / "04-security" / "README.md").read_text()
    assert "security-audit" in readme


def test_features_readme_references_document_feature_skill(tmp_path: Path):
    s = ProjectScaffolder(project_name="T", project_dir=tmp_path)
    s.scaffold_all()
    readme = (tmp_path / "docs" / "05-features" / "README.md").read_text()
    assert "document-feature" in readme


def test_research_readme_references_deep_research_skill(tmp_path: Path):
    s = ProjectScaffolder(project_name="T", project_dir=tmp_path)
    s.scaffold_all()
    readme = (tmp_path / "docs" / "07-research" / "README.md").read_text()
    assert "deep-research" in readme


def test_execution_plan_readme_references_sdd_tasks(tmp_path: Path):
    s = ProjectScaffolder(project_name="T", project_dir=tmp_path)
    s.scaffold_all()
    readme = (tmp_path / "docs" / "09-execution-plan" / "README.md").read_text()
    assert "sdd-tasks" in readme


# ---------------------------------------------------------------------------
# 5. Idempotency and overwrite semantics
# ---------------------------------------------------------------------------


def test_scaffold_is_idempotent(tmp_path: Path):
    s = ProjectScaffolder(project_name="T", project_dir=tmp_path)
    first = s.scaffold_all()
    assert len(first.created) == expected_file_count()

    # Second run — everything should be skipped, nothing created
    second = s.scaffold_all()
    assert len(second.created) == 0
    assert len(second.skipped) == expected_file_count()


def test_overwrite_replaces_existing(tmp_path: Path):
    ProjectScaffolder(project_name="T", project_dir=tmp_path).scaffold_all()

    target = tmp_path / "docs" / "01-context" / "business-context.md"
    target.write_text("USER EDIT — should be preserved without --overwrite")
    assert "USER EDIT" in target.read_text()

    # Without overwrite — preserved
    no_ov = ProjectScaffolder(project_name="T", project_dir=tmp_path).scaffold_all()
    assert "USER EDIT" in target.read_text()
    assert target in no_ov.skipped

    # With overwrite — replaced
    ov = ProjectScaffolder(project_name="T", project_dir=tmp_path, overwrite=True).scaffold_all()
    assert "USER EDIT" not in target.read_text()
    assert target in ov.created


# ---------------------------------------------------------------------------
# 6. Scaffold individual category
# ---------------------------------------------------------------------------


def test_scaffold_single_category_only(tmp_path: Path):
    s = ProjectScaffolder(project_name="T", project_dir=tmp_path)
    created = s.scaffold_category(3)  # 03-domain-risk

    # Only the one category should exist
    assert (tmp_path / "docs" / "03-domain-risk").exists()
    assert not (tmp_path / "docs" / "01-context").exists()
    assert len(created) == 4  # README + domain-model + risk-register + glossary (v1.1)


def test_scaffold_category_invalid_number(tmp_path: Path):
    s = ProjectScaffolder(project_name="T", project_dir=tmp_path)
    with pytest.raises(ValueError):
        s.scaffold_category(0)
    with pytest.raises(ValueError):
        s.scaffold_category(11)


# ---------------------------------------------------------------------------
# 7. Input validation
# ---------------------------------------------------------------------------


def test_empty_project_name_raises(tmp_path: Path):
    with pytest.raises(ValueError, match="project_name"):
        ProjectScaffolder(project_name="", project_dir=tmp_path)
    with pytest.raises(ValueError, match="project_name"):
        ProjectScaffolder(project_name="   ", project_dir=tmp_path)


def test_expected_category_paths_returns_10(tmp_path: Path):
    paths = expected_category_paths(tmp_path)
    assert len(paths) == 10
    assert set(paths.keys()) == set(EXPECTED_DIRS)


# ---------------------------------------------------------------------------
# 8. CLI end-to-end (real subprocess, real filesystem)
# ---------------------------------------------------------------------------


def test_cli_scaffolds_in_tmp(tmp_path: Path):
    """End-to-end: invoke scripts/project_scaffold.py as a real subprocess."""
    script = Path(__file__).resolve().parents[2] / "scripts" / "project_scaffold.py"
    assert script.exists()

    result = subprocess.run(
        [sys.executable, str(script),
         "--project-dir", str(tmp_path / "cli-proj"),
         "--project-name", "CLI Test",
         "--json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["created_count"] == expected_file_count()
    assert payload["skipped_count"] == 0
    assert (tmp_path / "cli-proj" / "docs" / "03-domain-risk" / "risk-register.md").exists()
    assert (tmp_path / "cli-proj" / "docs" / "06-backoffice" / "operations.md").exists()
