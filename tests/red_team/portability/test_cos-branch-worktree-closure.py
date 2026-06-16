from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ARTIFACT = REPO / "scripts" / "cos-branch-worktree-closure"


def test_cos_branch_worktree_closure_wrapper_has_portable_shell_contract() -> None:
    assert ARTIFACT.exists()
    assert ARTIFACT.stat().st_mode & 0o111
    result = subprocess.run(["bash", "-n", str(ARTIFACT)], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def test_cos_branch_worktree_closure_wrapper_runs_from_arbitrary_cwd(tmp_path: Path) -> None:
    result = subprocess.run(
        [str(ARTIFACT), "--project-dir", str(REPO), "--json"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert result.returncode in {0, 2}
    assert "cos.branch-worktree-closure.v1" in result.stdout
    assert "scripts/cos land" in result.stdout
