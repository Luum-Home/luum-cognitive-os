"""Behavior tests for the pre-commit primitive scope portability gate."""

from __future__ import annotations

import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def _run(args: list[str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def test_precommit_blocks_new_scope_both_script_without_portability_proof(tmp_path: Path) -> None:
    """A newly staged SCOPE: both primitive must not commit without a paired proof."""
    worktree = tmp_path / "scope-gate-worktree"
    add = _run(["git", "worktree", "add", "--detach", str(worktree), "HEAD"], REPO, timeout=120)
    assert add.returncode == 0, add.stderr
    try:
        script = worktree / "scripts" / "zz-scope-gate-negative"
        script.write_text(
            "#!/usr/bin/env bash\n"
            "# SCOPE: both\n"
            "echo should-not-commit-without-portability-proof\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        add_file = _run(["git", "add", "scripts/zz-scope-gate-negative"], worktree)
        assert add_file.returncode == 0, add_file.stderr

        result = _run(["bash", ".githooks/pre-commit"], worktree, timeout=120)

        output = result.stdout + result.stderr
        assert result.returncode != 0
        assert "SCOPE: both artifact lacks a paired portability proof" in output
        assert "scripts/cos-portability-proof-scaffold --artifact <path>" in output
    finally:
        _run(["git", "worktree", "remove", "--force", str(worktree)], REPO, timeout=120)
