from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import orchestrator_claim_gate

pytestmark = pytest.mark.unit


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "README.md").write_text("# test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_commit_body_prose_is_not_scanned_as_claim(tmp_path: Path) -> None:
    init_repo(tmp_path)
    result = orchestrator_claim_gate.evaluate(
        tmp_path,
        "check",
        command="git commit -m 'docs: wired core.hooksPath example into prose'",
    )
    assert result.ok
    assert result.findings == []


def test_status_claim_line_is_still_verified(tmp_path: Path) -> None:
    init_repo(tmp_path)
    result = orchestrator_claim_gate.evaluate(
        tmp_path,
        "check",
        command="git commit -m 'STATUS: archived hooks/nope.sh'",
    )
    assert not result.ok
    assert any("archived" in finding.message for finding in result.findings)


def test_done_count_line_is_still_verified(tmp_path: Path) -> None:
    init_repo(tmp_path)
    result = orchestrator_claim_gate.evaluate(
        tmp_path,
        "check",
        command="git commit -m 'done 3 scripts/nope.py'",
    )
    assert not result.ok
    assert any("done" in finding.message for finding in result.findings)
