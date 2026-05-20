from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL = REPO_ROOT / "install.sh"

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
    assert meta["skills_installed"] == len(CORE_SKILLS)

    installed_skills = {
        child.name
        for child in (tmp_path / ".cognitive-os" / "skills" / "cos").iterdir()
        if child.is_dir()
    }
    assert installed_skills == CORE_SKILLS
    assert installed_skills.isdisjoint(MAINTAINER_OR_LAB_SKILLS)
    assert (tmp_path / "AGENTS.md").is_file()
