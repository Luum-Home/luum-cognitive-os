from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "project_shell_ci.py"
spec = importlib.util.spec_from_file_location("project_shell_ci", MODULE_PATH)
assert spec and spec.loader
project_shell_ci = importlib.util.module_from_spec(spec)
sys.modules["project_shell_ci"] = project_shell_ci
spec.loader.exec_module(project_shell_ci)


def test_project_shell_ci_creates_canonical_drivers_and_workflow(tmp_path: Path) -> None:
    meta = project_shell_ci.project_shell_ci(tmp_path, "default")

    assert meta["commands_projected"] == 15
    assert (tmp_path / ".cognitive-os/scripts/cos/cos-status.sh").is_file()
    assert (tmp_path / "scripts/cos-status.sh").is_symlink()
    assert (tmp_path / ".github/workflows/cognitive-os-shell-ci.yml").is_file()
    assert str(Path(__file__).resolve().parents[2]) not in (tmp_path / ".github/workflows/cognitive-os-shell-ci.yml").read_text()
    saved = json.loads((tmp_path / ".cognitive-os/shell-ci-projection.json").read_text())
    assert saved["commands_projected"] == 15
