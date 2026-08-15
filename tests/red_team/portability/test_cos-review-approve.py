# SCOPE: os-only
"""Portability proof for scripts/cos-review-approve.

Freezing an approval must work in any git project from any cwd — the receipt
binds to the target project's tree, never to the OS repo.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts" / "cos-review-approve"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def test_approve_artifact_exists() -> None:
    assert ARTIFACT.exists()


def test_approve_freezes_in_an_arbitrary_project(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    _git(project, "init", "-q")
    _git(project, "config", "user.email", "t@t.com")
    _git(project, "config", "user.name", "t")
    _git(project, "checkout", "-q", "-b", "feature/p")
    (project / "f.py").write_text("z = 1\n", encoding="utf-8")
    _git(project, "add", "f.py")
    _git(project, "commit", "-q", "-m", "base")

    result = subprocess.run(
        [str(ARTIFACT), "--project-dir", str(project), "--json"],
        cwd=tmp_path,  # arbitrary cwd, not the project
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["approved"] is True
    assert payload["tree_hash"]
    # The receipt landed under the CONSUMER project, not the OS repo.
    assert (project / ".cognitive-os/receipts/review-approvals/feature_p.json").is_file()
