# SCOPE: os-only
"""Portability proof for cos_lib/reinvention_semantic.py.

``SemanticIndex`` backs the consumer-facing reinvention gate (SCOPE: both).
This proof pins that the module imports and its primary entry point
(``SemanticIndex.build_index`` / ``find_similar``) runs correctly from an
arbitrary working directory, scanning only ``cos_lib/``, ``hooks/``, and
``scripts/`` relative to the project root it is given, and persisting only
under that project's own ``.cognitive-os/`` — never anything that assumes it
is running inside the Cognitive OS source repo itself.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/reinvention_semantic.py"


def test_reinvention_semantic_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_reinvention_semantic", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_semantic_index_builds_and_queries_in_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: exercise the real entry point in a throwaway project.

    Builds a consumer project dir under ``tmp_path`` (standing in for a
    project that merely installed the OS — not the Cognitive OS source repo)
    with its own ``cos_lib/`` module, builds the index, and confirms a query
    for that module's own vocabulary finds it back — with the index
    persisted only inside the consumer project's own ``.cognitive-os/``.
    """
    project_dir = tmp_path / "consumer-project"
    (project_dir / "cos_lib").mkdir(parents=True)
    (project_dir / "cos_lib" / "throttle_agent_calls.py").write_text(
        '"""Throttle agent tool calls per minute to prevent runaway loops."""\n'
        "\n"
        "def throttle_agent_calls(limit):\n"
        "    return limit\n"
    )

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.reinvention_semantic import SemanticIndex\n"
        "idx = SemanticIndex()\n"
        "idx.build_index(%r)\n"
        "matches = idx.find_similar('throttle agent tool calls per minute', top_k=3)\n"
        "print(len(idx.items))\n"
        "print(len(matches))\n"
        "print(matches[0]['path'] if matches else 'NO_MATCH')\n"
    ) % (str(REPO_ROOT), str(project_dir))

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    out_lines = result.stdout.strip().splitlines()
    assert int(out_lines[0]) >= 1
    assert int(out_lines[1]) >= 1
    assert out_lines[2] == "cos_lib/throttle_agent_calls.py"

    index_path = project_dir / ".cognitive-os" / "reinvention-index.json"
    assert index_path.is_file()

    # Nothing was written outside the consumer project's own tree.
    assert not (tmp_path / ".cognitive-os").exists()
