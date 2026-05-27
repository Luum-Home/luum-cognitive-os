# SCOPE: os-only
"""Portability proof for skills/patch-release/SKILL.md."""

from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL = REPO_ROOT / "skills" / "patch-release" / "SKILL.md"
SCRIPT = REPO_ROOT / "scripts" / "cos-patch-release"


def test_patch_release_skill_commands_map_to_executable_dry_run(tmp_path: Path) -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "scripts/cos-patch-release prepare" in text
    result = subprocess.run(
        [str(SCRIPT), "--project-dir", str(tmp_path), "publish", "--version", "9.9.9", "--dry-run"],
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "codex/release-v9.9.9" in result.stdout
    assert "scripts/merge-to-main.sh" in result.stdout
