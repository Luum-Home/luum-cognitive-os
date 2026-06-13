# SCOPE: os-only
"""Portability proof for scripts/cos-skill-selection-report."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/cos-skill-selection-report"


def test_cos_skill_selection_report_artifact_exists() -> None:
    assert ARTIFACT.exists()


def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: must write project-local state outside the OS repo cwd."""
    project = tmp_path / "consumer"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    (project / "package.json").write_text('{"dependencies":{"react":"latest"}}\n', encoding="utf-8")
    result = subprocess.run(
        [
            str(ARTIFACT),
            "--project-dir",
            str(project),
            "--process-id",
            "portable-skill-selection",
            "--changed-file",
            "src/App.tsx",
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=outside,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert "frontend" in payload["stack_signals"]
    assert "component" in payload["change_signals"]
    assert any(item["name"] == "frontend-dod" for item in payload["recommended_skills"])
    assert (project / ".cognitive-os/process-loops/portable-skill-selection/skill-selection-report.json").exists()
