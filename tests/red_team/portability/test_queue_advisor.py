# SCOPE: os-only
"""Portability proof for cos_lib/queue_advisor.py.

``QueueAdvisor`` backs consumer-facing queue-drain tooling (SCOPE: both). This
proof pins that the module imports and its primary entry point
(``QueueAdvisor.advise`` -> algorithmic v1 scoring) runs correctly from an
arbitrary working directory, reading only ``.cognitive-os/`` paths and
``cognitive-os.yaml`` relative to the project dir it is given — never
anything that assumes it is running inside the Cognitive OS source repo
itself.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/queue_advisor.py"


def test_queue_advisor_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_queue_advisor", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_advise_reorders_queue_in_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: exercise the real entry point in a throwaway project.

    Builds a consumer project dir under ``tmp_path`` (standing in for a
    project that merely installed the OS — not the Cognitive OS source repo)
    with no ``.cognitive-os`` state at all, and confirms ``advise()`` still
    scores and reorders queue items using its documented defaults (no daily
    limit file -> default budget cap; no tasks file -> empty dependency map).
    """
    project_dir = tmp_path / "consumer-project"
    project_dir.mkdir()

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.queue_advisor import QueueAdvisor\n"
        "advisor = QueueAdvisor(project_dir=%r)\n"
        "items = [\n"
        "    {'id': 'a', 'description': 'short task', 'model': 'haiku', 'priority': 5, 'enqueued_at': ''},\n"
        "    {'id': 'b', 'description': 'other task', 'model': 'opus', 'priority': 5, 'enqueued_at': ''},\n"
        "]\n"
        "result = advisor.advise(items, mode='algorithmic')\n"
        "print(len(result))\n"
        "print(all('advisor_score' in r and 'advisor_reason' in r for r in result))\n"
        "print(advisor.format_advice(result).splitlines()[0])\n"
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
    assert out_lines[0] == "2"
    assert out_lines[1] == "True"
    assert out_lines[2].startswith("Launching '")

    # Nothing was written outside the consumer project's own tree.
    assert not (tmp_path / ".cognitive-os").exists()
