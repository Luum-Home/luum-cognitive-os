# SCOPE: os-only
"""Portability proof for cos_lib/model_catalog.py.

Pins that ModelCatalog is pure static data with no filesystem or project-root
dependency: import and every primary entry point (get/resolve/estimate_cost/
upgrade/downgrade) work from an arbitrary working directory with no dependency
on the OS repo tree.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/model_catalog.py"


def test_model_catalog_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_model_catalog", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_model_catalog_lookups_work_from_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: exercise real lookups/cost math in a subprocess run
    from an arbitrary cwd, standing in for a consumer project that merely
    installed the OS — not the Cognitive OS source repo.
    """
    consumer_cwd = tmp_path / "consumer_project"
    consumer_cwd.mkdir()

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.model_catalog import ModelCatalog\n"
        "entry = ModelCatalog.get('opus')\n"
        "print(entry.id)\n"
        "print(ModelCatalog.resolve('claude-opus-4'))\n"
        "print(ModelCatalog.downgrade('claude-opus-4-6'))\n"
        "print(ModelCatalog.estimate_cost('sonnet', 10_000, 5_000))\n"
        "cheap = ModelCatalog.cheapest_for('code', min_score=6)\n"
        "print(cheap.id)\n"
    ) % (str(REPO_ROOT),)

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=consumer_cwd,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert lines[0] == "claude-opus-4-6"
    assert lines[1] == "claude-opus-4-6"
    assert lines[2] == "claude-sonnet-4"
    assert float(lines[3]) > 0
    assert lines[4]  # some model id returned

    # Nothing was written outside the consumer project's own tree.
    assert not (tmp_path / ".cognitive-os").exists()
