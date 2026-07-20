# SCOPE: os-only
"""Portability proof for cos_lib/git_context.py.

``git_context`` backs ``hooks/git-context-capture.sh`` (SCOPE: both), a
consumer-facing Stop hook. This proof pins that the module imports and its
primary entry point (``capture_session_git_context``) runs correctly from an
arbitrary working directory, operating only on a ``project_dir`` argument
passed in by the caller — never anything that assumes it is running inside
the Cognitive OS source repo itself.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/git_context.py"


def test_git_context_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_git_context", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_capture_session_git_context_works_in_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: exercise the real entry point in a throwaway repo.

    Initializes a bare git repo under ``tmp_path`` (standing in for a consumer
    project that merely installed the OS — not the Cognitive OS source repo),
    makes two commits, and confirms ``capture_session_git_context`` reports
    the branch, commit range, and file-change stats using only the
    ``project_dir`` argument — no OS-repo-relative paths.
    """
    project_dir = tmp_path / "consumer-project"
    project_dir.mkdir()

    subprocess.run(["git", "init", "-q"], cwd=project_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project_dir, check=True)

    (project_dir / "README.md").write_text("hello\n")
    subprocess.run(["git", "add", "README.md"], cwd=project_dir, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=project_dir, check=True)

    start_sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    (project_dir / "feature.txt").write_text("new feature\n")
    subprocess.run(["git", "add", "feature.txt"], cwd=project_dir, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "feat: add feature"], cwd=project_dir, check=True)

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.git_context import capture_session_git_context\n"
        "ctx = capture_session_git_context(%r, commit_start=%r)\n"
        "print(ctx.branch)\n"
        "print(len(ctx.commits))\n"
        "print(ctx.files_modified)\n"
    ) % (str(REPO_ROOT), str(project_dir), start_sha)

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    out_lines = result.stdout.strip().splitlines()
    assert out_lines[0]  # branch name resolved, not empty
    assert int(out_lines[1]) == 1  # exactly one commit in the range
    assert int(out_lines[2]) == 1  # one file changed in that commit
