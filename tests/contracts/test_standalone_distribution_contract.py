from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]


def test_release_pipeline_artifacts_are_declared() -> None:
    goreleaser = yaml.safe_load((REPO / ".goreleaser.yaml").read_text(encoding="utf-8"))
    assert goreleaser["project_name"] == "cognitive-os"
    assert goreleaser["builds"][0]["dir"] == "cmd/cos"
    assert goreleaser["builds"][0]["main"] == "."
    assert set(goreleaser["builds"][0]["goos"]) >= {"darwin", "linux"}
    assert set(goreleaser["builds"][0]["goarch"]) >= {"amd64", "arm64"}
    release_workflow = REPO / ".github" / "workflows" / "cos-binary-release.yml"
    assert release_workflow.exists()
    workflow_text = release_workflow.read_text(encoding="utf-8")
    assert "scripts/cos-patch-release doctor --strict --contract-only --json" in workflow_text
    assert "go run . derive check" in workflow_text
    assert "go run . quarantine audit" in workflow_text
    assert "homebrew_casks" in goreleaser
    assert goreleaser["homebrew_casks"][0]["repository"]["name"] == "homebrew-tap"
    assert goreleaser["homebrew_casks"][0]["binaries"] == ["cos"]
    installer = REPO / "scripts" / "install-goreleaser.sh"
    assert installer.exists()
    assert "goreleaser release --snapshot --clean --skip=publish" in installer.read_text(encoding="utf-8")


def test_homebrew_formula_has_no_checksum_placeholder() -> None:
    formula = (REPO / "Formula" / "cognitive-os.rb").read_text(encoding="utf-8")
    for token in ("UPDATE", "WITH", "ACTUAL", "SHA256"):
        assert token not in formula
    assert "sha256" not in formula
    assert "head " in formula
    assert 'bin/"cos"' in formula


def test_homebrew_local_canary_is_documented() -> None:
    canary = REPO / "scripts" / "cos-homebrew-local-canary"
    assert canary.exists()
    script = canary.read_text(encoding="utf-8")
    assert "git -C \"$ROOT\" archive" in script
    assert "brew tap-new" in script
    assert "brew install --build-from-source" in script
    assert "COS_RUN_HOMEBREW_CANARY=1" in script

    readiness = (REPO / "docs" / "04-Concepts" / "architecture" / "standalone-ship-readiness-2026-05-06.md").read_text(
        encoding="utf-8"
    )
    release = (REPO / "docs" / "01-Build-Log" / "release" / "v1.0-release-criteria.md").read_text(encoding="utf-8")

    for doc in (readiness, release):
        assert "scripts/cos-homebrew-local-canary" in doc
        assert "COS_RUN_HOMEBREW_CANARY=1" in doc
        assert "temporary local tap" in doc
        assert "Git HEAD source tarball" in doc
        assert "brew install --build-from-source" in doc
        assert "external tap" in doc


def test_standalone_service_and_headless_artifacts_exist() -> None:
    assert (REPO / "infra" / "cosd" / "systemd" / "cosd.service").exists()
    assert (REPO / "infra" / "cosd" / "k8s" / "cosd-local.yaml").exists()
    assert (REPO / "scripts" / "cos-root").exists()
    assert (REPO / "scripts" / "cos-headless-pipeline").exists()


def test_cos_root_resolves_without_git_checkout(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    result = subprocess.run(
        ["bash", str(REPO / "scripts" / "cos-root"), "project"],
        cwd=tmp_path,
        env={"COGNITIVE_OS_PROJECT_DIR": str(project), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == str(project)


def test_goreleaser_dependency_is_installed_through_repo_script() -> None:
    deps = yaml.safe_load((REPO / "manifests" / "dependencies.yaml").read_text(encoding="utf-8"))
    tools = {tool["name"]: tool for tool in deps["tools"]}
    goreleaser = tools["goreleaser"]
    assert goreleaser["category"] == "cli"
    for platform in ("macos", "linux", "windows_wsl"):
        command = goreleaser["install"][platform]["command"]
        assert command == "bash scripts/install-goreleaser.sh --install"
