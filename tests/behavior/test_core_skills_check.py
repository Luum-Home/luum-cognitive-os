"""Behavior tests for scripts/cos-core-skills-check.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CORE_SKILLS_CHECK = PROJECT_ROOT / "scripts" / "cos-core-skills-check.sh"

CORE_SKILLS = [
    "compose-prompt",
    "exhaustive-prompt",
    "agent-dashboard",
    "auto-refine",
    "verification-before-completion",
    "plan-feature",
    "session-backlog",
    "resource-governor",
    "paperclip-dashboard",
]


def test_core_skills_check_uses_canonical_runtime_env():
    """The checker should resolve the project root from canonical runtime env vars."""
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(PROJECT_ROOT)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)

    result = subprocess.run(
        ["bash", str(CORE_SKILLS_CHECK), "--json"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=env,
        timeout=30,
    )

    assert result.returncode in {0, 1}, result.stderr
    data = json.loads(result.stdout)
    assert data["total"] == 10


def test_core_skills_check_accepts_canonical_only_skill_surface(tmp_path):
    """The checker should accept a project that exposes core skills only canonically."""
    project = tmp_path / "project"
    canonical_skills = project / ".cognitive-os" / "skills" / "cos"
    scripts_dir = project / "scripts"
    canonical_skills.mkdir(parents=True)
    scripts_dir.mkdir(parents=True)

    for skill_name in CORE_SKILLS:
        skill_dir = canonical_skills / skill_name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            f"name: {skill_name}\n"
            "version: 1.0.0\n"
            "description: Test skill\n"
            "triggers: []\n"
            "---\n"
            "\n"
            f"# {skill_name}\n"
        )

    cos_status = scripts_dir / "cos-status.sh"
    cos_status.write_text("#!/usr/bin/env bash\nexit 0\n")
    cos_status.chmod(0o755)

    result = subprocess.run(
        ["bash", str(CORE_SKILLS_CHECK), "--json", "--root", str(project)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["ok"] is True
    for skill in data["skills"]:
        assert skill["ok"] is True, skill
