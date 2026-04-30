"""Governance hooks consume persisted test artifacts instead of rerunning pytest."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTO_VERIFY = REPO_ROOT / "hooks" / "auto-verify.sh"
DOD_GATE = REPO_ROOT / "hooks" / "dod-gate.sh"
HELPER = REPO_ROOT / "scripts" / "cos_test_artifact_status.py"


def _project_with_artifact(tmp_path: Path, *, failures: int = 0) -> Path:
    project = tmp_path / "project"
    scripts = project / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(HELPER, scripts / HELPER.name)
    reports = project / ".cognitive-os" / "reports" / "test-runs"
    run = reports / "20260101T000000Z-tests-unit"
    run.mkdir(parents=True)
    failed_text = f", {failures} failed" if failures else ""
    run.joinpath("summary.txt").write_text(f"10 passed{failed_text}, 0 skipped in 1.00s\n", encoding="utf-8")
    run.joinpath("inventory.md").write_text("# Inventory\n", encoding="utf-8")
    run.joinpath("junit.xml").write_text(
        f'<testsuite tests="10" failures="{failures}" errors="0" skipped="0"></testsuite>',
        encoding="utf-8",
    )
    latest = reports / "latest"
    latest.symlink_to(run, target_is_directory=True)
    (project / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
    (project / "cognitive-os.yaml").write_text("project:\n  phase: production\n", encoding="utf-8")
    return project


def _add_coverage_artifact(project: Path, *, coverage_pct: int = 85) -> None:
    reports = project / ".cognitive-os" / "reports" / "coverage"
    run = reports / "20260101T000001Z-coverage"
    run.mkdir(parents=True)
    run.joinpath("summary.txt").write_text(
        f"=== Summary ===\n  Composite:              {coverage_pct}% ({coverage_pct}/100)\n",
        encoding="utf-8",
    )
    run.joinpath("coverage.json").write_text(
        json.dumps(
            {
                "composite_pct": coverage_pct,
                "composite_covered": coverage_pct,
                "composite_total": 100,
            }
        ),
        encoding="utf-8",
    )
    latest = reports / "latest"
    latest.symlink_to(run, target_is_directory=True)


def _add_quality_artifact(project: Path, *, blocking_count: int = 0) -> None:
    reports = project / ".cognitive-os" / "reports" / "test-quality"
    run = reports / "20260101T000002Z-quality"
    run.mkdir(parents=True)
    run.joinpath("summary.txt").write_text("Test Quality Audit\n", encoding="utf-8")
    run.joinpath("quality.json").write_text(
        json.dumps({"total": 10, "blocking_count": blocking_count}),
        encoding="utf-8",
    )
    latest = reports / "latest"
    latest.symlink_to(run, target_is_directory=True)


def _run_hook(hook: Path, project: Path, payload: dict) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "CLAUDE_PROJECT_DIR": str(project),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "VALKEY_DISABLED": "1",
        }
    )
    return subprocess.run(
        ["bash", str(hook)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(project),
        env=env,
        timeout=20,
    )


def test_artifact_status_helper_reads_latest_junit(tmp_path: Path):
    project = _project_with_artifact(tmp_path)
    result = subprocess.run(
        ["python3", str(HELPER), "--project-root", str(project), "--json"],
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "pass"
    assert data["tests"] == 10
    assert data["summary_txt"].endswith("summary.txt")
    assert data["inventory_md"].endswith("inventory.md")
    assert data["junit_xml"].endswith("junit.xml")


def test_artifact_status_helper_reads_latest_coverage_artifact(tmp_path: Path):
    project = _project_with_artifact(tmp_path)
    _add_coverage_artifact(project, coverage_pct=79)
    result = subprocess.run(
        [
            "python3",
            str(HELPER),
            "--project-root",
            str(project),
            "--artifact-kind",
            "coverage",
            "--coverage-threshold",
            "80",
            "--json",
        ],
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "fail"
    assert data["coverage_pct"] == 79
    assert data["summary_txt"].endswith("summary.txt")


def test_artifact_status_helper_reads_latest_quality_artifact(tmp_path: Path):
    project = _project_with_artifact(tmp_path)
    _add_quality_artifact(project, blocking_count=0)
    result = subprocess.run(
        [
            "python3",
            str(HELPER),
            "--project-root",
            str(project),
            "--artifact-kind",
            "quality",
            "--json",
        ],
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "pass"
    assert data["blocking_count"] == 0


def test_auto_verify_test_criterion_consumes_latest_artifact(tmp_path: Path):
    project = _project_with_artifact(tmp_path)
    payload = {
        "tool_name": "Agent",
        "tool_input": {"prompt": "verify"},
        "tool_response": "Implementation complete.\n\nACCEPTANCE CRITERIA:\n1. Tests pass with 0 failed.\n",
    }
    result = _run_hook(AUTO_VERIFY, project, payload)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "AUTO-VERIFY: PASS" in result.stdout
    assert "artifact:" in result.stdout


def test_auto_verify_coverage_criterion_consumes_latest_coverage_artifact(tmp_path: Path):
    project = _project_with_artifact(tmp_path)
    _add_coverage_artifact(project, coverage_pct=85)
    payload = {
        "tool_name": "Agent",
        "tool_input": {"prompt": "verify"},
        "tool_response": "Implementation complete.\n\nACCEPTANCE CRITERIA:\n1. Coverage >= 80%.\n",
    }
    result = _run_hook(AUTO_VERIFY, project, payload)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "AUTO-VERIFY: PASS" in result.stdout
    assert "coverage artifact:" in result.stdout


def test_dod_gate_uses_artifacts_for_test_and_coverage_criteria(tmp_path: Path):
    project = _project_with_artifact(tmp_path)
    _add_coverage_artifact(project, coverage_pct=85)
    response = "\n".join(
        [
            "Complexity: medium",
            "Done implementing the feature.",
            "Build success with exit code 0.",
            "lint clean.",
            "documentation updated in README.md.",
        ]
    )
    payload = {"tool_name": "Agent", "tool_input": {"prompt": "feature"}, "tool_response": {"content": response}}
    result = _run_hook(DOD_GATE, project, payload)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "Missing DoD criteria" not in result.stdout
