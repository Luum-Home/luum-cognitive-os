# SCOPE: os-only
"""Paired portability proof for templates/confidentiality.yaml.

The template's whole purpose is to be installed into a *consumer* project at
``<project>/.cognitive-os/confidentiality.yaml`` and read back by
``cos_lib.confidentiality_scanner.load_protected_terms``. The falsification
probe therefore installs it into a throwaway project root and loads it from
there: a template that drifted away from its parser, or a loader that only works
against this repo, fails here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ARTIFACT = REPO_ROOT / "templates/confidentiality.yaml"


def test_loads_from_arbitrary_project_root(tmp_path: Path) -> None:
    from cos_lib.confidentiality_scanner import load_protected_terms

    installed = tmp_path / ".cognitive-os" / "confidentiality.yaml"
    installed.parent.mkdir(parents=True)
    installed.write_text(ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")

    terms = load_protected_terms(str(installed))
    assert terms is not None

    from_repo = load_protected_terms(str(ARTIFACT))
    assert terms == from_repo, "loader result depends on where the template lives"


def test_every_shipped_key_is_consumed_by_the_loader() -> None:
    """Falsification probe: a key the parser ignores is dead config."""
    from cos_lib.confidentiality_scanner import load_protected_terms

    shipped = yaml.safe_load(ARTIFACT.read_text(encoding="utf-8")) or {}
    assert shipped, "template shipped with no keys at all"

    terms = load_protected_terms(str(ARTIFACT))
    for key in shipped:
        assert hasattr(terms, key), f"template key {key!r} is not read by load_protected_terms"
