"""Tests for ADR-208 dependency adoption evidence gate."""
from __future__ import annotations

import subprocess
from pathlib import Path

from lib.dependency_adoption_gate import evaluate_staged, is_adoption_evidence, is_dependency_manifest


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _init_repo(repo: Path) -> Path:
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    return repo


def test_dependency_manifest_detection() -> None:
    assert is_dependency_manifest("pyproject.toml")
    assert is_dependency_manifest("services/api/package.json")
    assert is_dependency_manifest("requirements/observability.txt")
    assert is_dependency_manifest("requirements-dev.txt")
    assert not is_dependency_manifest("README.md")


def test_adoption_evidence_detection() -> None:
    assert is_adoption_evidence("docs/reports/repo-scout-leftpad.md")
    assert is_adoption_evidence("docs/reports/repo-forensics-leftpad.md")
    assert is_adoption_evidence("manifests/imported-pattern-closures.yaml")
    assert not is_adoption_evidence("docs/reports/random.md")


def test_blocks_staged_dependency_addition_without_evidence(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = [\n  "leftpad>=1.0",\n]\n',
        encoding="utf-8",
    )
    _git(repo, "add", "pyproject.toml")

    result = evaluate_staged(repo)

    assert result.status == "block"
    assert result.exit_code == 2
    assert result.dependency_files == ["pyproject.toml"]
    assert result.evidence_files == []
    assert any("leftpad" in line for line in result.added_dependency_lines)


def test_allows_staged_dependency_addition_with_repo_scout_evidence(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = [\n  "leftpad>=1.0",\n]\n',
        encoding="utf-8",
    )
    evidence = repo / "docs/reports/repo-scout-leftpad.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("# Repo Scout — leftpad\n\nLicense: MIT\n", encoding="utf-8")
    _git(repo, "add", "pyproject.toml", "docs/reports/repo-scout-leftpad.md")

    result = evaluate_staged(repo)

    assert result.status == "pass"
    assert result.exit_code == 0
    assert result.evidence_files == ["docs/reports/repo-scout-leftpad.md"]


def test_inventory_uses_tracked_files_not_local_dependency_caches(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    cache_manifest = repo / "node_modules/pkg/package.json"
    cache_manifest.parent.mkdir(parents=True)
    cache_manifest.write_text('{"name":"pkg"}\n', encoding="utf-8")
    _git(repo, "add", "pyproject.toml")
    _git(repo, "commit", "-m", "init")

    from lib.dependency_adoption_gate import current_dependency_inventory

    inventory = current_dependency_inventory(repo)

    assert "pyproject.toml" in inventory["dependency_manifests"]
    assert "node_modules/pkg/package.json" not in inventory["dependency_manifests"]
