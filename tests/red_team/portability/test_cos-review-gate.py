# SCOPE: os-only
"""Portability proof for scripts/cos-review-gate.

The gate must deny/allow based on the target project's tree from any cwd, and
must never pass vacuously when there is no approval.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE = REPO_ROOT / "scripts" / "cos-review-gate"
APPROVE = REPO_ROOT / "scripts" / "cos-review-approve"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "consumer"
    project.mkdir()
    _git(project, "init", "-q")
    _git(project, "config", "user.email", "t@t.com")
    _git(project, "config", "user.name", "t")
    _git(project, "checkout", "-q", "-b", "feature/g")
    (project / "f.py").write_text("z = 1\n", encoding="utf-8")
    _git(project, "add", "f.py")
    _git(project, "commit", "-q", "-m", "base")
    return project


def test_gate_artifact_exists() -> None:
    assert GATE.exists()


def test_gate_denies_without_approval_from_arbitrary_cwd(tmp_path: Path) -> None:
    project = _project(tmp_path)
    result = subprocess.run(
        [str(GATE), "--project-dir", str(project)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "no-approval" in (result.stdout + result.stderr)


def test_gate_allows_after_approval_then_denies_on_mutation(tmp_path: Path) -> None:
    project = _project(tmp_path)
    assert subprocess.run([str(APPROVE), "--project-dir", str(project)], cwd=tmp_path, capture_output=True).returncode == 0
    assert subprocess.run([str(GATE), "--project-dir", str(project)], cwd=tmp_path, capture_output=True).returncode == 0

    (project / "f.py").write_text("z = 2\n", encoding="utf-8")
    _git(project, "add", "f.py")
    _git(project, "commit", "-q", "-m", "mutate")
    denied = subprocess.run([str(GATE), "--project-dir", str(project)], cwd=tmp_path, capture_output=True, text=True)
    assert denied.returncode == 2
    assert "tree-mismatch" in (denied.stdout + denied.stderr)
