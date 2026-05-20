"""Behavior coverage for Op Stability Phase 3 adaptive profiles."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO = Path(__file__).resolve().parents[2]
COS = REPO / "scripts" / "cos"


def git(project: Path, *args: str) -> None:
    result = subprocess.run(["git", *args], cwd=project, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def make_repo(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    git(project, "init", "-b", "feature/adaptive")
    git(project, "config", "user.email", "adaptive@example.invalid")
    git(project, "config", "user.name", "Adaptive Test")
    (project / "README.md").write_text("ok\n", encoding="utf-8")
    git(project, "add", "README.md")
    git(project, "commit", "-m", "init")
    return project


def run_cos_profile(project: Path, *args: str) -> dict:
    result = subprocess.run(
        [str(COS), "profile", "explain", "--json", *args],
        cwd=REPO,
        env={"PATH": __import__("os").environ.get("PATH", ""), "COGNITIVE_OS_PROJECT_DIR": str(project)},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_cos_profile_explain_uses_resource_lease_signal(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    leases = project / ".cognitive-os" / "runtime" / "resource-leases"
    leases.mkdir(parents=True)
    (leases / "registry.json").write_text(json.dumps({"resource": "registry", "expires_at": 4102444800}) + "\n", encoding="utf-8")

    payload = run_cos_profile(project)

    assert payload["profile"] == "strict"
    assert payload["signals"]["active_resource_leases"] == 1
    assert "active resource leases=1" in payload["reasons"]


def test_cos_profile_explain_logs_scoped_override(tmp_path: Path) -> None:
    project = make_repo(tmp_path)

    payload = run_cos_profile(project, "--override", "lean", "--override-ttl-seconds", "30")

    assert payload["override"] is True
    assert payload["override_scope"] == str(project.resolve())
    log = project / ".cognitive-os" / "metrics" / "adaptive-profile-overrides.jsonl"
    assert log.exists()
    assert json.loads(log.read_text().splitlines()[-1])["profile"] == "lean"
