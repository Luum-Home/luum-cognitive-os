# SCOPE: os-only
"""Portability proof for cos_lib/memory_governance.py.

Pins that the ADR-261 typed-memory policy table is pure computation with no
filesystem or project-root dependency: import and its primary entry points
(get_policy/is_stale/assess_freshness/boosted_score) work from an arbitrary
working directory with no dependency on the OS repo tree.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/memory_governance.py"


def test_memory_governance_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_memory_governance", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_policy_lookups_work_from_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: exercise real policy/staleness/boost math in a
    subprocess run from an arbitrary cwd, standing in for a consumer project
    that merely installed the OS — not the Cognitive OS source repo.
    """
    consumer_cwd = tmp_path / "consumer_project"
    consumer_cwd.mkdir()

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.memory_governance import get_policy, is_stale, assess_freshness, boosted_score\n"
        "policy = get_policy('blocker')\n"
        "print(policy.recall_boost)\n"
        "print(is_stale(1_000_000, 'blocker'))\n"
        "result = assess_freshness(1_000_000, 'blocker')\n"
        "print(result.state)\n"
        "print(boosted_score(1.0, 'blocker'))\n"
        "print(get_policy('unknown_type').recall_boost)\n"
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
    assert lines[0] == "1.8"
    assert lines[1] == "True"
    assert lines[2] == "stale"
    assert lines[3] == "1.8"
    assert lines[4] == "1.0"

    # Nothing was written outside the consumer project's own tree.
    assert not (tmp_path / ".cognitive-os").exists()
