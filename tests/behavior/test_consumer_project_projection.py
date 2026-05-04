from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
COS_INIT = REPO_ROOT / "scripts" / "cos_init.py"


@pytest.mark.parametrize(
    ("harness", "settings_file"),
    [
        ("claude", ".claude/settings.json"),
        ("codex", ".codex/hooks.json"),
    ],
)
def test_default_install_projects_core_primitives_into_consumer_project(tmp_path: Path, harness: str, settings_file: str) -> None:
    result = subprocess.run(
        [sys.executable, str(COS_INIT), "--default", "--harness", harness],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    install_meta = json.loads((tmp_path / ".cognitive-os" / "install-meta.json").read_text())
    assert install_meta["harness"] == harness
    assert install_meta["rules_installed"] >= 13
    assert install_meta["hooks_installed"] >= 37
    assert install_meta["skills_installed"] >= 8
    assert (tmp_path / settings_file).exists()
    assert (tmp_path / ".cognitive-os" / "hooks" / "cos" / "session-init.sh").exists()
    assert (tmp_path / ".cognitive-os" / "rules" / "cos" / "RULES-COMPACT.md").exists()
    assert (tmp_path / ".cognitive-os" / "skills" / "cos" / "cos-status" / "SKILL.md").exists()
