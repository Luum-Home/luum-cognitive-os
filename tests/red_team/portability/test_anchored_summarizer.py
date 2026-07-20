# SCOPE: os-only
"""Portability proof for cos_lib/anchored_summarizer.py.

Pins that AnchoredSummarizer.extract_*/create_anchor/persist_anchor work from
an arbitrary working directory, using only paths passed in by the caller
(session_dir), with no dependency on the OS repo tree.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/anchored_summarizer.py"


def test_anchored_summarizer_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_anchored_summarizer", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_persist_anchor_writes_under_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: create + persist a real anchor, in a subprocess run
    from an arbitrary cwd, and read the written anchor.json back.

    Proves the summarizer only writes under the caller-supplied session_dir
    and does not assume it is running inside the Cognitive OS source repo.
    """
    consumer_cwd = tmp_path / "consumer_project"
    consumer_cwd.mkdir()
    session_dir = tmp_path / "sessions" / "current"

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.anchored_summarizer import AnchoredSummarizer\n"
        "instance = AnchoredSummarizer(session_dir=%r)\n"
        "anchor = instance.create_anchor('Decided to use SQLite. "
        "Fixed src/app.py today. Still need to write tests.')\n"
        "result = instance.persist_anchor(anchor, to_file=True, to_engram=False)\n"
        "print(result['file_path'])\n"
    ) % (str(REPO_ROOT), str(session_dir))

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=consumer_cwd,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    anchor_file = session_dir / "anchor.json"
    assert anchor_file.exists()
    data = json.loads(anchor_file.read_text(encoding="utf-8"))
    assert "decisions" in data
    assert "files_touched" in data
    assert "task_state" in data
    assert any("src/app.py" in f for f in data["files_touched"])
