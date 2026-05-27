"""Behavior tests for ADR-208 dependency adoption gate CLI."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _init_repo(repo: Path) -> Path:
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    return repo


@pytest.mark.behavior
def test_dependency_adoption_gate_cli_blocks_without_evidence(project_root: Path, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["leftpad>=1.0"]\n',
        encoding="utf-8",
    )
    _git(repo, "add", "pyproject.toml")

    result = subprocess.run(
        [
            str(project_root / "scripts/cos-dependency-adoption-gate"),
            "--project-dir",
            str(repo),
            "--staged",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "block"
    assert payload["dependency_files"] == ["pyproject.toml"]
    assert payload["evidence_files"] == []


@pytest.mark.behavior
def test_dependency_adoption_gate_cli_passes_with_evidence(project_root: Path, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "requirements.txt").write_text("httpx==0.27.0\n", encoding="utf-8")
    evidence = repo / "docs/06-Daily/reports/repo-forensics-httpx.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("# Repo Forensics — httpx\n", encoding="utf-8")
    _git(repo, "add", "requirements.txt", "docs/06-Daily/reports/repo-forensics-httpx.md")

    result = subprocess.run(
        [
            str(project_root / "scripts/cos-dependency-adoption-gate"),
            "--project-dir",
            str(repo),
            "--staged",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["evidence_files"] == ["docs/06-Daily/reports/repo-forensics-httpx.md"]


@pytest.mark.behavior
def test_dependency_adoption_gate_cli_allows_go_toolchain_directive(project_root: Path, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "go.mod").write_text("module demo\n\ngo 1.25.6\n", encoding="utf-8")
    _git(repo, "add", "go.mod")
    _git(repo, "commit", "-m", "initial go module")
    (repo / "go.mod").write_text("module demo\n\ngo 1.26.3\n", encoding="utf-8")
    _git(repo, "add", "go.mod")

    result = subprocess.run(
        [
            str(project_root / "scripts/cos-dependency-adoption-gate"),
            "--project-dir",
            str(repo),
            "--staged",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["added_dependency_lines"] == []


@pytest.mark.behavior
def test_dependency_adoption_gate_cli_coverage_aware(project_root: Path, tmp_path: Path) -> None:
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests/dependencies.yaml").write_text(
        """schema_version: 1
python:
  required: []
  groups: {}
tools: []
mcp_servers: []
profiles:
  default:
    python_groups: []
    tools_required: []
    tools_recommended: []
    mcp_servers_recommended: []
  full:
    python_groups: []
    tools_required: []
    tools_recommended: []
    mcp_servers_recommended: []
""",
        encoding="utf-8",
    )
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/probe.sh").write_text("command -v shellcheck >/dev/null\n", encoding="utf-8")

    result = subprocess.run(
        [
            str(project_root / "scripts/cos-dependency-adoption-gate"),
            "--project-dir",
            str(tmp_path),
            "--coverage-aware",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "cos-deps-triage.v1"
    assert payload["summary"]["actionable"] >= 1
