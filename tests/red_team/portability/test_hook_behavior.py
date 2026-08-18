# SCOPE: os-only
"""Paired portability proof for scripts/hook_behavior.py.

This artifact is a library module, not a CLI: it has no ``__main__`` block and
no argparse, so ``--help`` exits 0 with empty stdout and proves nothing (the
scaffold's default template would have asserted exactly that non-event).

The portable claim it does make is that its classification works on any hook
path handed to it, from any cwd. This proof imports it from a foreign project
root and classifies a real hook copied there.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/hook_behavior.py"


def _load():
    spec = importlib.util.spec_from_file_location("hook_behavior_under_proof", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: classification must not read the process cwd."""
    hook_src = REPO_ROOT / "hooks" / "secret-detector.sh"
    relocated = tmp_path / "hooks" / hook_src.name
    relocated.parent.mkdir(parents=True)
    relocated.write_text(hook_src.read_text(encoding="utf-8"), encoding="utf-8")

    module = _load()
    previous = Path.cwd()
    os.chdir(tmp_path)
    try:
        from_foreign = module.classify(relocated.stem, relocated)
    finally:
        os.chdir(previous)

    from_repo = module.classify(hook_src.stem, hook_src)

    # Same source, same verdict, regardless of where it sits or where we stand.
    assert from_foreign[0] == from_repo[0]
    assert from_foreign[1] == from_repo[1]
    assert from_foreign[0], "classifier returned an empty behaviour class"
