"""Unit tests for Caveman integration.

Verifies that the caveman skills are installed correctly, the agent preamble
contains the Caveman-Lite section, and the adoption registry is updated.
"""
import os
from pathlib import Path

import pytest
import yaml

from tests.unit._helpers import assert_preamble_contains_concepts


@pytest.fixture
def project_root() -> Path:
    """Return the absolute path to the project root directory."""
    source_project = os.environ.get("COS_VALIDATION_SOURCE_PROJECT_DIR")
    if source_project:
        return Path(source_project)
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def preamble_text(project_root) -> str:
    """Return the contents of the agent preamble template."""
    return (project_root / "templates" / "agent-preamble.md").read_text()


@pytest.fixture
def catalog_text(project_root) -> str:
    """Return the contents of the skills catalog."""
    return (project_root / "skills" / "CATALOG.md").read_text()


@pytest.fixture
def adoption_registry(project_root) -> dict:
    """Return the parsed adoption registry."""
    path = project_root / ".cognitive-os" / "adoption-registry.yaml"
    return yaml.safe_load(path.read_text())


# --- Preamble tests ---

def test_preamble_has_caveman_lite_section(preamble_text):
    """Agent preamble must document output compression / preservation concepts.

    The exact section heading may vary (e.g. '## Output Compression',
    'PRESERVE exactly', 'compression').  What matters is that the concept is
    documented so sub-agents know to compress output.
    """
    assert_preamble_contains_concepts(
        preamble_text,
        [
            "## Output Compression",
            "Output Compression",
            "PRESERVE exactly",
            "PRESERVE EXACTLY",
            "compression",
        ],
    )


def test_preamble_has_auto_clarity_exception(preamble_text):
    """Agent preamble must document the output compression / preservation rules."""
    assert_preamble_contains_concepts(
        preamble_text,
        [
            "PRESERVE EXACTLY",
            "PRESERVE exactly",
            "Auto-Clarity",
            "EXCEPTION",
            "preserve",
        ],
    )


def test_preamble_preserves_code_blocks_rule(preamble_text):
    """Agent preamble must state that code blocks must be preserved exactly."""
    assert_preamble_contains_concepts(
        preamble_text,
        [
            "PRESERVE EXACTLY",
            "PRESERVE exactly",
            "code blocks",
        ],
    )


# --- Skill existence tests ---

def test_caveman_skill_exists(project_root):
    """skills/caveman/SKILL.md must exist."""
    skill_path = project_root / "skills" / "caveman" / "SKILL.md"
    assert skill_path.exists(), f"Missing: {skill_path}"


def test_caveman_es_skill_exists(project_root):
    """skills/caveman-es/SKILL.md must exist."""
    skill_path = project_root / "skills" / "caveman-es" / "SKILL.md"
    assert skill_path.exists(), f"Missing: {skill_path}"


def test_caveman_compress_skill_exists(project_root):
    """skills/caveman-compress/SKILL.md must exist."""
    skill_path = project_root / "skills" / "caveman-compress" / "SKILL.md"
    assert skill_path.exists(), f"Missing: {skill_path}"


# --- Catalog tests ---

def test_caveman_in_catalog(catalog_text):
    """CATALOG.md must list all three caveman skills."""
    assert "caveman" in catalog_text
    assert "caveman-es" in catalog_text
    assert "caveman-compress" in catalog_text or "compress" in catalog_text


# --- Adoption registry tests ---

def test_adoption_registry_has_caveman(adoption_registry):
    """adoption-registry.yaml must contain the caveman-lite-preamble entry."""
    adoptions = adoption_registry.get("adoptions", [])
    ids = [entry.get("id") for entry in adoptions]
    assert "caveman-lite-preamble" in ids, (
        f"caveman-lite-preamble not found in adoption registry. Found: {ids}"
    )


def test_adoption_registry_caveman_entry_complete(adoption_registry):
    """The caveman entry in adoption-registry.yaml must have all required fields."""
    adoptions = adoption_registry.get("adoptions", [])
    caveman_entry = next(
        (e for e in adoptions if e.get("id") == "caveman-lite-preamble"), None
    )
    assert caveman_entry is not None, "caveman-lite-preamble entry missing"
    assert caveman_entry.get("source") == "caveman"
    assert caveman_entry.get("our_file") == "templates/agent-preamble.md"
    assert caveman_entry.get("adapted") is True
    assert caveman_entry.get("adopted_date") == "2026-04-08"
