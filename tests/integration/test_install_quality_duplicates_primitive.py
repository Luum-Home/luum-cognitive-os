from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_cos_init_installs_quality_duplicates_binary(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    (project / "README.md").write_text("consumer\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "cos_init.py"), "--default", "--harness", "codex"],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    wrapper = project / ".cognitive-os" / "bin" / "cos-quality-duplicates"
    engine = project / ".cognitive-os" / "bin" / "cos_quality_duplicates.py"
    assert wrapper.exists()
    assert engine.exists()
    smoke = subprocess.run([str(wrapper), "--project-root", str(project), "--include", "README.md"], text=True, capture_output=True, check=False)
    assert smoke.returncode == 0, smoke.stderr
