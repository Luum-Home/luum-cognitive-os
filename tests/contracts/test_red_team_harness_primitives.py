from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[2]
VERIFY_ARCHIVED = ROOT / "scripts" / "verify-archived.sh"
PLAN_VALIDATOR = ROOT / "hooks" / "plan-claim-validator.sh"


def run(cmd: list[str], cwd: Path, *, input_text: str | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(cmd, cwd=str(cwd), input=input_text, env=merged, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def test_verify_archived_succeeds_when_archive_present_and_source_absent(tmp_path: Path) -> None:
    archive = tmp_path / "attic" / "scripts"
    source = tmp_path / "scripts"
    archive.mkdir(parents=True)
    source.mkdir()
    (archive / "old.sh").write_text("archived\n", encoding="utf-8")

    result = run(["bash", str(VERIFY_ARCHIVED), "--archive-dir", str(archive), "--source-dir", str(source), "--manifest", "old.sh", "--json"], tmp_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["verified"] is True
    assert payload["results"][0]["archive_present"] is True
    assert payload["results"][0]["source_absent"] is True


def test_verify_archived_fails_if_source_still_present(tmp_path: Path) -> None:
    archive = tmp_path / "attic" / "scripts"
    source = tmp_path / "scripts"
    archive.mkdir(parents=True)
    source.mkdir()
    (archive / "old.sh").write_text("archived\n", encoding="utf-8")
    (source / "old.sh").write_text("live\n", encoding="utf-8")

    result = run(["bash", str(VERIFY_ARCHIVED), "--archive-dir", str(archive), "--source-dir", str(source), "--manifest", "old.sh", "--json"], tmp_path)

    assert result.returncode == 1
    assert json.loads(result.stdout)["verified"] is False


def test_verify_archived_fails_if_archive_missing(tmp_path: Path) -> None:
    archive = tmp_path / "attic" / "scripts"
    source = tmp_path / "scripts"
    archive.mkdir(parents=True)
    source.mkdir()

    result = run(["bash", str(VERIFY_ARCHIVED), "--archive-dir", str(archive), "--source-dir", str(source), "--manifest", "old.sh", "--json"], tmp_path)

    assert result.returncode == 2
    assert json.loads(result.stdout)["results"][0]["archive_present"] is False


def test_verify_archived_fails_on_stale_config_reference(tmp_path: Path) -> None:
    archive = tmp_path / "attic" / "scripts"
    source = tmp_path / "scripts"
    config = tmp_path / "config"
    archive.mkdir(parents=True)
    source.mkdir()
    config.mkdir()
    (archive / "old.sh").write_text("archived\n", encoding="utf-8")
    (config / "hooks.txt").write_text("scripts/old.sh\n", encoding="utf-8")

    result = run(["bash", str(VERIFY_ARCHIVED), "--archive-dir", str(archive), "--source-dir", str(source), "--manifest", "old.sh", "--config-globs", "config/*.txt", "--json"], tmp_path)

    assert result.returncode == 3
    payload = json.loads(result.stdout)
    assert payload["verified"] is False
    assert payload["results"][0]["config_refs"]


def jq_required() -> None:
    if shutil.which("jq") is None:
        pytest.skip("plan-claim-validator requires jq")


def validator_payload(file_path: Path, content: str, tool: str = "Write") -> str:
    return json.dumps({"tool_name": tool, "tool_input": {"file_path": str(file_path), "content": content, "new_string": content}})


def test_plan_claim_validator_blocks_unverified_done_claim_in_consumer_plan(tmp_path: Path) -> None:
    jq_required()
    plan = tmp_path / "plans" / "sprint.md"
    plan.parent.mkdir()
    content = "- [x] ship the thing\n"

    result = run(["bash", str(PLAN_VALIDATOR)], tmp_path, input_text=validator_payload(plan, content), env={"COGNITIVE_OS_PROJECT_DIR": str(tmp_path), "COS_PLAN_VALIDATOR_MODE": "block", "COS_PLAN_GLOB": "plans/**/*.md"})

    assert result.returncode == 2
    assert "without (verified:" in result.stderr


def test_plan_claim_validator_allows_verified_done_claim(tmp_path: Path) -> None:
    jq_required()
    plan = tmp_path / "plans" / "sprint.md"
    plan.parent.mkdir()
    content = "- [x] ship the thing (verified: python3 -m pytest tests/contracts/test_red_team_harness_primitives.py -q) (work_id: 0123456789abcdef)\n"

    result = run(["bash", str(PLAN_VALIDATOR)], tmp_path, input_text=validator_payload(plan, content), env={"COGNITIVE_OS_PROJECT_DIR": str(tmp_path), "COS_PLAN_VALIDATOR_MODE": "block", "COS_PLAN_GLOB": "plans/**/*.md"})

    assert result.returncode == 0, result.stderr


def test_plan_claim_validator_ignores_non_plan_file(tmp_path: Path) -> None:
    jq_required()
    file_path = tmp_path / "src" / "app.py"
    file_path.parent.mkdir()

    result = run(["bash", str(PLAN_VALIDATOR)], tmp_path, input_text=validator_payload(file_path, "- [x] not a plan\n"), env={"COGNITIVE_OS_PROJECT_DIR": str(tmp_path), "COS_PLAN_VALIDATOR_MODE": "block", "COS_PLAN_GLOB": "plans/**/*.md"})

    assert result.returncode == 0, result.stderr
