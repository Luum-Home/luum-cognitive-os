from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL = REPO_ROOT / "install.sh"
STATUS = REPO_ROOT / "scripts" / "cos-status.sh"
BOUNDARY = REPO_ROOT / "manifests" / "primitive-install-boundary.yaml"

CORE_SKILLS = {
    "auto-refine",
    "compose-prompt",
    "cos-status",
    "exhaustive-prompt",
    "plan-feature",
    "resource-governor",
    "session-backlog",
    "verification-before-completion",
}

MAINTAINER_OR_LAB_SKILLS = {
    "agent-stress-test",
    "cognitive-os-test",
    "cos-install-operations",
    "cos-maintainer-operations",
    "hook-timing",
    "phoenix-trace-ui",
    "primitive-harvester",
    "queue-drain",
    "redteam-harness",
    "validate-release",
}


def test_install_profile_core_keeps_default_consumer_boundary(tmp_path: Path) -> None:
    """ADR-093: install.sh --profile=core is an alias for the consumer-safe default boundary."""
    result = subprocess.run(
        [
            "bash",
            str(INSTALL),
            "--from",
            str(REPO_ROOT),
            "--profile=core",
            "--harness=agents-md",
            "--force",
            "--skip-manifest-check",
        ],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=90,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Profile: default (source: flag)" in result.stdout

    meta = json.loads((tmp_path / ".cognitive-os" / "install-meta.json").read_text())
    assert meta["mode"] == "default"
    assert meta["harness"] == "agents-md"
    assert meta["active_distribution"] == "core"
    assert meta["install_boundary_manifest"] == "manifests/primitive-install-boundary.yaml"
    assert meta["skills_installed"] == len(CORE_SKILLS)

    boundary = yaml.safe_load(BOUNDARY.read_text())
    core_boundary = set()
    for primitive_paths in boundary["profiles"]["default"]["primitives"].values():
        core_boundary.update(primitive_paths)

    projected = {
        f"hooks/{child.name}"
        for child in (tmp_path / ".cognitive-os" / "hooks" / "cos").iterdir()
        if child.is_file() and child.suffix == ".sh"
    }
    projected.update(
        f"rules/{child.name}"
        for child in (tmp_path / ".cognitive-os" / "rules" / "cos").iterdir()
        if child.is_file() and child.suffix == ".md"
    )
    projected.update(
        f"skills/{child.name}/SKILL.md"
        for child in (tmp_path / ".cognitive-os" / "skills" / "cos").iterdir()
        if child.is_dir()
    )
    assert projected
    assert projected <= core_boundary

    installed_skills = {
        child.name
        for child in (tmp_path / ".cognitive-os" / "skills" / "cos").iterdir()
        if child.is_dir()
    }
    assert installed_skills == CORE_SKILLS
    assert (tmp_path / ".cognitive-os" / "hooks" / "cos" / "research-compliance-guard.sh").is_file()
    assert (tmp_path / ".cognitive-os" / "rules" / "cos" / "license-policy.md").is_file()
    assert (tmp_path / ".cognitive-os" / "rules" / "cos" / "research-first-protocol.md").is_file()
    assert installed_skills.isdisjoint(MAINTAINER_OR_LAB_SKILLS)
    assert (tmp_path / "AGENTS.md").is_file()

    status_env = os.environ.copy()
    status_env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    status_env["COGNITIVE_OS_HARNESS"] = "agents-md"
    status = subprocess.run(
        ["bash", str(STATUS), "--json"],
        cwd=REPO_ROOT,
        env=status_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    assert status.returncode == 0, status.stderr + status.stdout
    status_json = json.loads(status.stdout)
    assert status_json["profile"] == "default"
    assert status_json["active_distribution"] == "core"
