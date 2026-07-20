# SCOPE: os-only
"""Portability proof for cos_lib/stash_sha.py.

Pins that stash-identity resolution (``list_stashes``, ``resolve_top_stash_sha``,
``resolve_sha_to_ref``, ``find_by_subject``) imports and works against a real
git repo from an arbitrary working directory — the module only ever runs
``git -C <repo>`` against the ``repo`` argument passed in by the caller, never
anything that assumes it is running inside the Cognitive OS source repo.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/stash_sha.py"


def test_stash_sha_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_stash_sha", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_stash_identity_round_trips_in_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: create a real stash in a throwaway git repo, in a
    subprocess run from an arbitrary cwd, and resolve its identity by SHA.

    Proves the module has no hidden dependency on running inside the
    Cognitive OS source repo (e.g. relative paths, sibling manifests) — it
    only ever touches the ``repo`` path explicitly passed by the caller.
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
    subprocess.run(["git", "add", "dirty.txt"], cwd=project_dir, check=True)
    subprocess.run(
        ["git", "stash", "push", "-m", "portability-proof-stash"],
        cwd=project_dir,
        check=True,
    )

    unrelated_cwd = tmp_path / "not-the-repo"
    unrelated_cwd.mkdir()

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.stash_sha import list_stashes, resolve_top_stash_sha, "
        "resolve_sha_to_ref, find_by_subject\n"
        "entries = list_stashes(%r)\n"
        "assert len(entries) == 1, entries\n"
        "top_sha = resolve_top_stash_sha(%r)\n"
        "assert top_sha == entries[0].sha\n"
        "ref = resolve_sha_to_ref(%r, top_sha)\n"
        "assert ref == 'stash@{0}'\n"
        "by_subject = find_by_subject(%r, 'portability-proof-stash')\n"
        "assert len(by_subject) == 1\n"
        "assert by_subject[0].sha == top_sha\n"
        "print('STASH_SHA_OK')\n"
    ) % (
        str(REPO_ROOT),
        str(project_dir),
        str(project_dir),
        str(project_dir),
        str(project_dir),
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=unrelated_cwd,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "STASH_SHA_OK" in result.stdout, result.stdout + result.stderr
