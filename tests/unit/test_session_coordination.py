from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lib.session_coordination import (
    acquire_claim,
    adr_tombstone_findings,
    read_claims,
    record_worktree_intake,
    release_claim,
    worktree_intake_findings,
)


pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos_session_coordination.py"


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=path, check=True, stdout=subprocess.PIPE)


def test_claim_ledger_blocks_same_adr_number_for_other_session(tmp_path: Path) -> None:
    first = acquire_claim(tmp_path, kind="adr-number", subject="171", session_id="session-a")
    second = acquire_claim(tmp_path, kind="adr-number", subject="ADR-171", session_id="session-b")

    assert first.status == "acquired"
    assert second.status == "blocked"
    assert second.held_by and second.held_by["session_id"] == "session-a"
    assert read_claims(tmp_path)[0]["subject"] == "ADR-171"


def test_release_claim_allows_next_session(tmp_path: Path) -> None:
    assert acquire_claim(tmp_path, kind="path", subject="docs/02-Decisions/adrs/ADR-171.md", session_id="s1").status == "acquired"
    assert release_claim(tmp_path, kind="path", subject="docs/02-Decisions/adrs/ADR-171.md", session_id="s1").status == "released"

    assert acquire_claim(tmp_path, kind="path", subject="docs/02-Decisions/adrs/ADR-171.md", session_id="s2").status == "acquired"


def test_adr_tombstone_findings_block_active_adr_file(tmp_path: Path) -> None:
    adrs = tmp_path / "docs" / "02-Decisions" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-171-reject-integration.md").write_text("# ADR-171: Reject Integration\n", encoding="utf-8")

    findings = adr_tombstone_findings(tmp_path, number=171, session_id="session-b")

    assert findings
    assert findings[0].status == "FAIL"
    assert "active ADR file" in findings[0].message


def test_adr_tombstone_findings_block_other_session_claim(tmp_path: Path) -> None:
    acquire_claim(tmp_path, kind="adr-number", subject="ADR-179", session_id="rules-session")

    findings = adr_tombstone_findings(tmp_path, number=179, session_id="tombstone-session")

    assert findings
    assert "claimed by another live session" in findings[0].message


def test_worktree_intake_requires_record_for_sibling_worktree(tmp_path: Path) -> None:
    init_repo(tmp_path)
    sibling = tmp_path.parent / f"{tmp_path.name}-sibling"
    subprocess.run(["git", "worktree", "add", "-b", "other-session", str(sibling)], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    try:
        findings = worktree_intake_findings(tmp_path)
        assert findings
        assert findings[0].status == "FAIL"

        record_worktree_intake(tmp_path, other_worktree=str(sibling), policy="read-only", summary="audited only", session_id="s1")

        assert worktree_intake_findings(tmp_path) == []
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(sibling)], cwd=tmp_path, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_cli_claim_outputs_json_and_blocks_conflict(tmp_path: Path) -> None:
    first = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--project-dir",
            str(tmp_path),
            "--json",
            "claim",
            "--kind",
            "adr-number",
            "--subject",
            "ADR-173",
            "--session-id",
            "session-a",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert first.returncode == 0
    assert json.loads(first.stdout)["claim"]["subject"] == "ADR-173"

    second = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--project-dir",
            str(tmp_path),
            "--json",
            "claim",
            "--kind",
            "adr-number",
            "--subject",
            "173",
            "--session-id",
            "session-b",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert second.returncode == 2
    assert json.loads(second.stdout)["held_by"]["session_id"] == "session-a"
