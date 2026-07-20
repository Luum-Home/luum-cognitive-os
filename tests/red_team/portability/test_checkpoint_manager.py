# SCOPE: os-only
"""Portability proof for cos_lib/checkpoint_manager.py.

``checkpoint_manager`` backs ``hooks/auto-checkpoint.sh`` (SCOPE: both), a
consumer-facing PostToolUse hook. This proof pins that the module imports and
its primary entry point (``CheckpointManager.create_checkpoint``) runs
correctly from an arbitrary working directory, using only a git repo and
``.cognitive-os/`` paths relative to the project dir — never anything that
assumes it is running inside the Cognitive OS source repo itself.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/checkpoint_manager.py"


def test_checkpoint_manager_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_checkpoint_manager", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_create_checkpoint_works_in_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: exercise the real entry point in a throwaway project.

    Initializes a bare git repo under ``tmp_path`` (standing in for a consumer
    project that merely installed the OS — not the Cognitive OS source repo),
    writes a dirty file, and confirms ``create_checkpoint`` produces a
    checkpoint record without touching anything outside ``tmp_path``.
    """
    project_dir = tmp_path / "consumer-project"
    project_dir.mkdir()

    subprocess.run(["git", "init", "-q"], cwd=project_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project_dir, check=True)

    (project_dir / "README.md").write_text("hello\n")
    subprocess.run(["git", "add", "README.md"], cwd=project_dir, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=project_dir, check=True)

    (project_dir / "dirty.txt").write_text("uncommitted work\n")

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.checkpoint_manager import CheckpointManager\n"
        "mgr = CheckpointManager(project_dir=%r)\n"
        "cp = mgr.create_checkpoint(note='portability-proof')\n"
        "print(cp.checkpoint_id)\n"
        "print(cp.uncommitted_changes)\n"
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
    checkpoint_id = out_lines[0]
    uncommitted_changes = int(out_lines[1])
    assert uncommitted_changes == 1

    meta_path = project_dir / ".cognitive-os" / "checkpoints" / f"{checkpoint_id}.json"
    assert meta_path.is_file()
    data = json.loads(meta_path.read_text())
    assert data["files_modified"] == ["dirty.txt"]

    # Nothing was written outside the consumer project's own tree.
    assert not (tmp_path / ".cognitive-os").exists()
