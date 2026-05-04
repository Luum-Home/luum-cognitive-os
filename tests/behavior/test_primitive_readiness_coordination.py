from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

ROOT = Path(__file__).resolve().parents[2]
CLAIM_TASK = ROOT / "scripts" / "claim_task.py"
CONTRACT_DOC = ROOT / "docs" / "architecture" / "concurrency-safety-core-consumer-contract.md"
READINESS_PLAN = ROOT / "docs" / "architecture" / "primitive-readiness-continuity-plan.md"


def run_claim(project_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLAIM_TASK), "--project-dir", str(project_dir), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def payload(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def test_primitive_readiness_task_claim_blocks_duplicate_work_and_releases(tmp_path: Path) -> None:
    task_id = "primitive-readiness-protected-install-surfaces"
    expected_files = [
        "manifests/primitive-readiness-protected-install-surfaces.yaml",
        "manifests/primitive-lifecycle.yaml",
        "scripts/primitive_readiness_ledger.py",
    ]
    expected_args = [arg for path in expected_files for arg in ("--expected-file", path)]

    first = run_claim(
        tmp_path,
        "acquire",
        task_id,
        "--session-id",
        "session-a",
        "--agent-id",
        "codex-a",
        "--scope",
        "primitive-readiness",
        "--ttl-seconds",
        "7200",
        *expected_args,
    )
    assert first.returncode == 0
    first_payload = payload(first)
    assert first_payload["status"] == "acquired"
    assert first_payload["claim"]["expected_files"] == expected_files
    assert first_payload["claim"]["scope"] == "primitive-readiness"

    duplicate = run_claim(
        tmp_path,
        "acquire",
        task_id,
        "--session-id",
        "session-b",
        "--agent-id",
        "codex-b",
        "--scope",
        "primitive-readiness",
        "--ttl-seconds",
        "7200",
        *expected_args,
    )
    assert duplicate.returncode == 2
    duplicate_payload = payload(duplicate)
    assert duplicate_payload["status"] == "blocked"
    assert duplicate_payload["held_by"]["session_id"] == "session-a"
    assert duplicate_payload["held_by"]["expected_files"] == expected_files

    released = run_claim(
        tmp_path,
        "release",
        task_id,
        "--session-id",
        "session-a",
        "--agent-id",
        "codex-a",
    )
    assert released.returncode == 0
    assert payload(released)["status"] == "released"

    reacquired = run_claim(
        tmp_path,
        "acquire",
        task_id,
        "--session-id",
        "session-b",
        "--agent-id",
        "codex-b",
        "--scope",
        "primitive-readiness",
        "--ttl-seconds",
        "7200",
        *expected_args,
    )
    assert reacquired.returncode == 0
    assert payload(reacquired)["status"] == "acquired"


def test_docs_connect_task_claim_primitive_to_primitive_readiness_workflow() -> None:
    contract = CONTRACT_DOC.read_text(encoding="utf-8")
    plan = READINESS_PLAN.read_text(encoding="utf-8")

    assert "task claim ledger" in contract
    assert "scripts/claim_task.py" in contract
    assert "lib/task_claim_ledger.py" in contract
    assert "first live claim win" in contract

    assert "## Coordination preflight" in plan
    assert "python3 scripts/claim_task.py acquire <task_id>" in plan
    assert "--scope primitive-readiness" in plan
    assert "not a file lock" in plan
