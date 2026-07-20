# SCOPE: os-only
"""Portability proof for cos_lib/__init__.py.

``cos_lib/__init__.py`` is the package marker that every consumer projection
copies unconditionally, which is why it is scoped ``both`` rather than
``os-only``. This proof pins the two properties that scope depends on: the
marker must be inert (no imports to drag os-only modules into a consumer
install) and the package must import from an arbitrary working directory.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib" / "__init__.py"


def test_package_marker_artifact_exists() -> None:
    assert ARTIFACT.exists()


def test_package_marker_is_inert() -> None:
    """No imports and no executable statements.

    A consumer projection copies this file unconditionally. Any import here
    would pull its target into every consumer install, bypassing the SCOPE
    filter that keeps os-only modules out of consumer projections.
    """
    tree = ast.parse(ARTIFACT.read_text(encoding="utf-8"), filename=str(ARTIFACT))

    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert not imports, f"package marker must not import: {imports}"

    executable = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
        )
    ]
    assert not executable, f"package marker must be inert, found: {executable}"


def test_package_imports_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: importing the package must not depend on cwd."""
    result = subprocess.run(
        [sys.executable, "-c", "import cos_lib; print(cos_lib.__name__)"],
        cwd=tmp_path,
        env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin"},
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "cos_lib" in result.stdout
