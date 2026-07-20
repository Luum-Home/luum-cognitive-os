# SCOPE: os-only
"""Portability proof for cos_lib/adr_router.py.

``adr_router`` backs ``hooks/adr-relevance-suggest.sh`` (SCOPE: both), a
consumer-facing UserPromptSubmit hook. This proof pins that the module
imports and its primary entry point (``AdrRouter.top_matches``) runs
correctly from an arbitrary working directory, indexing only
``docs/02-Decisions/adrs`` relative to a ``project_root`` passed in by the
caller — never anything that assumes it is running inside the Cognitive OS
source repo itself.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/adr_router.py"


def test_adr_router_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_adr_router", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_top_matches_works_in_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: exercise the real entry point in a throwaway project.

    Builds a minimal ``docs/02-Decisions/adrs`` tree under ``tmp_path``
    (standing in for a consumer project that merely installed the OS — not
    the Cognitive OS source repo), writes one tagged ADR, and confirms
    ``top_matches`` finds it from a subprocess run with an unrelated cwd —
    proving the index is built entirely from the ``project_root`` argument.
    """
    project_dir = tmp_path / "consumer-project"
    adrs_dir = project_dir / "docs" / "02-Decisions" / "adrs"
    adrs_dir.mkdir(parents=True)

    (adrs_dir / "ADR-001-widget-caching.md").write_text(
        "---\n"
        "adr: 1\n"
        "title: Widget Caching Strategy\n"
        "status: accepted\n"
        "tags: [widget-caching, performance]\n"
        "---\n\n"
        "## Context\n\n"
        "Widget caching reduces redundant recomputation for repeated requests.\n"
    )

    unrelated_cwd = tmp_path / "somewhere-else"
    unrelated_cwd.mkdir()

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.adr_router import AdrRouter\n"
        "router = AdrRouter(project_root=%r)\n"
        "matches = router.top_matches('how do we handle widget-caching for performance?', n=3)\n"
        "print(len(matches))\n"
        "print(matches[0].adr_id if matches else '')\n"
    ) % (str(REPO_ROOT), str(project_dir))

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=unrelated_cwd,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    out_lines = result.stdout.strip().splitlines()
    assert int(out_lines[0]) >= 1, result.stdout + result.stderr
    assert out_lines[1] == "ADR-001"


def test_top_matches_degrades_gracefully_when_adrs_dir_absent(tmp_path: Path) -> None:
    """Falsification probe: a consumer project with no ADR directory at all
    (never having authored one) must not error — only return an empty list.
    """
    project_dir = tmp_path / "bare-consumer-project"
    project_dir.mkdir()

    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_adr_router_bare", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    router = module.AdrRouter(project_root=project_dir)
    assert router.top_matches("anything at all", n=3) == []
