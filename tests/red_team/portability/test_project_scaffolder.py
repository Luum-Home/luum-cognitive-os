# SCOPE: os-only
"""Portability proof for lib/project_scaffolder.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "lib/project_scaffolder.py"


def test_project_scaffolder_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_project_scaffolder", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
