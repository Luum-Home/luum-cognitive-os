from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "cos-test-laptop-bg"


def test_cos_test_laptop_bg_is_executable_and_arbitrary_cwd_safe(tmp_path: Path) -> None:
    assert SCRIPT.exists()
    assert SCRIPT.stat().st_mode & 0o111
    syntax = subprocess.run(["bash", "-n", str(SCRIPT)], cwd=tmp_path, text=True, capture_output=True, check=False)
    assert syntax.returncode == 0, syntax.stderr
    result = subprocess.run(
        [str(SCRIPT), "--json", "--dry-run", "--log-dir", str(tmp_path), "--", "echo", "portable"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["cwd"] == str(ROOT)
    assert payload["command"] == "echo portable"
