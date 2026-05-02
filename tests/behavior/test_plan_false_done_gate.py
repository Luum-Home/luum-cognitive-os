from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFY = REPO_ROOT / "scripts" / "verify-plan-claims.py"


def run_verify(project: Path, plan: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(VERIFY), str(plan), "--project-dir", str(project)],
        cwd=project,
        text=True,
        capture_output=True,
        timeout=10,
    )


@pytest.fixture
def project_with_plan(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "docs" / "archive" / "hooks").mkdir(parents=True)
    (project / "hooks").mkdir(parents=True)
    (project / ".claude").mkdir(parents=True)
    (project / ".codex").mkdir(parents=True)
    return project


@pytest.mark.behavior
def test_archive_claim_fails_when_original_or_config_reference_survives(project_with_plan: Path):
    project = project_with_plan
    (project / "docs" / "archive" / "hooks" / "example-hook.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (project / "hooks" / "example-hook.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (project / "cognitive-os.yaml").write_text("hooks:\n  example: example-hook.sh\n", encoding="utf-8")
    plan = project / "plan.md"
    plan.write_text("- [x] Archive hook example-hook.sh\n", encoding="utf-8")

    result = run_verify(project, plan)
    assert result.returncode == 2
    assert "original still exists" in result.stdout
    assert "config still references example-hook.sh" in result.stdout


@pytest.mark.behavior
def test_archive_claim_passes_after_bilateral_conditions_hold(project_with_plan: Path):
    project = project_with_plan
    (project / "docs" / "archive" / "hooks" / "example-hook.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (project / "cognitive-os.yaml").write_text("hooks: {}\n", encoding="utf-8")
    plan = project / "plan.md"
    plan.write_text("- [x] Archive hook example-hook.sh\n", encoding="utf-8")

    result = run_verify(project, plan)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


@pytest.mark.behavior
def test_generic_high_stakes_done_claim_requires_inline_verified_record(project_with_plan: Path):
    project = project_with_plan
    plan = project / "plan.md"
    plan.write_text("- [x] Done production safety migration\n", encoding="utf-8")

    result = run_verify(project, plan)
    assert result.returncode == 2
    assert "missing inline bilateral proof" in result.stdout

    plan.write_text("- [x] Done production safety migration (verified: pytest scenario passed)\n", encoding="utf-8")
    result = run_verify(project, plan)
    assert result.returncode == 0, result.stdout + result.stderr
