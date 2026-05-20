from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.orchestrator_claim_gate import evaluate


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def _init(repo: Path) -> None:
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "base.txt")
    _git(repo, "commit", "-m", "seed")


def test_pre_commit_blocks_duplicate_staged_patch_id_against_main(tmp_path: Path) -> None:
    _init(tmp_path)
    (tmp_path / "landed.txt").write_text("same change\n", encoding="utf-8")
    _git(tmp_path, "add", "landed.txt")
    _git(tmp_path, "commit", "-m", "feat: landed change")
    _git(tmp_path, "checkout", "-b", "worker", "HEAD~1")

    (tmp_path / "landed.txt").write_text("same change\n", encoding="utf-8")
    _git(tmp_path, "add", "landed.txt")

    result = evaluate(tmp_path, "pre-commit")

    assert not result.ok
    assert any("duplicate staged diff" in finding.message for finding in result.findings)


def test_pre_commit_allows_unique_staged_patch_id(tmp_path: Path) -> None:
    _init(tmp_path)
    (tmp_path / "unique.txt").write_text("unique change\n", encoding="utf-8")
    _git(tmp_path, "add", "unique.txt")

    result = evaluate(tmp_path, "pre-commit")

    assert result.ok, [finding.message for finding in result.findings]
