"""Behavior tests for scripts/cos-ghost-skills.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GHOST_SKILLS_CHECK = PROJECT_ROOT / "scripts" / "cos-ghost-skills.sh"


def test_ghost_skills_uses_canonical_skill_surface(tmp_path):
    """The checker should use canonical skills when no driver projection exists."""
    project = tmp_path / "project"
    canonical_skills = project / ".cognitive-os" / "skills" / "cos"
    metrics_dir = project / ".cognitive-os" / "metrics"
    canonical_skills.mkdir(parents=True)
    metrics_dir.mkdir(parents=True)

    for skill_name in ("alpha-skill", "beta-skill"):
        skill_dir = canonical_skills / skill_name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {skill_name}\n")

    (metrics_dir / "skill-usage.jsonl").write_text(
        '{"timestamp":"2030-01-01T00:00:00.000000Z","name":"alpha-skill"}\n'
    )

    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)

    result = subprocess.run(
        ["bash", str(GHOST_SKILLS_CHECK), "--days", "3650", "--json"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=env,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["skills_surface"].endswith(".cognitive-os/skills/cos")
    assert data["exposed_count"] == 2
    assert data["invoked_count"] == 1
    assert data["ghost_count"] == 1
    assert data["ghosts"] == ["beta-skill"]
