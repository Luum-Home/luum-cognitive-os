"""Smoke tests for scripts/regen_catalog_bullets.py (B3 parser audit).

Two tests:
1. Import check — confirms the module is importable by its snake_case name.
2. Functional smoke — runs build_bullets() against a tmp_path with a synthetic
   SKILL.md and confirms the output format is correct.
"""
from __future__ import annotations

import sys
import importlib
from pathlib import Path

import pytest

# Ensure repo root is on sys.path so lib/ and scripts/ are importable
REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Test 1: Import check
# ---------------------------------------------------------------------------


def test_module_imports_successfully():
    """scripts/regen_catalog_bullets.py is importable as a module."""
    spec = importlib.util.spec_from_file_location(
        "regen_catalog_bullets",
        REPO_ROOT / "scripts" / "regen_catalog_bullets.py",
    )
    assert spec is not None, "spec_from_file_location returned None — file missing?"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    # Confirm key callables are present
    assert callable(getattr(mod, "build_bullets", None))
    assert callable(getattr(mod, "regen", None))


# ---------------------------------------------------------------------------
# Test 2: Functional smoke — build_bullets against synthetic SKILL.md
# ---------------------------------------------------------------------------


def test_build_bullets_with_synthetic_skills(tmp_path, monkeypatch):
    """build_bullets() returns correctly formatted bullet lines for synthetic skills."""
    # Build a minimal skills directory with two SKILL.md files
    skills_dir = tmp_path / "skills"
    (skills_dir / "alpha-skill").mkdir(parents=True)
    (skills_dir / "alpha-skill" / "SKILL.md").write_text(
        "---\nname: alpha-skill\ndescription: Does alpha things\nversion: 1.0\n---\n# Body\n"
    )
    (skills_dir / "beta-skill").mkdir(parents=True)
    (skills_dir / "beta-skill" / "SKILL.md").write_text(
        "<!-- SCOPE: both -->\n---\nname: beta-skill\ndescription: Does beta things\nversion: 2.0\n---\n"
    )

    # Point the module at our tmp skills directory and a dummy CATALOG.md
    catalog = tmp_path / "CATALOG.md"
    catalog.write_text("# Skills Catalog\n\nIntro text here.\n")

    spec = importlib.util.spec_from_file_location(
        "regen_catalog_bullets",
        REPO_ROOT / "scripts" / "regen_catalog_bullets.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    # Patch module-level constants to point at tmp_path
    monkeypatch.setattr(mod, "SKILLS_DIR", skills_dir)
    monkeypatch.setattr(mod, "CATALOG", catalog)

    bullets = mod.build_bullets()

    assert len(bullets) == 2, f"Expected 2 bullets, got {len(bullets)}: {bullets}"
    # Output format: "- **name** — description\n"
    joined = "".join(bullets)
    assert "- **alpha-skill**" in joined
    assert "Does alpha things" in joined
    assert "- **beta-skill**" in joined
    assert "Does beta things" in joined
    # Sorted alphabetically
    assert joined.index("alpha") < joined.index("beta")
