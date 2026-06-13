from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "cos-test-slow-report"


def test_cos_test_slow_report_wrapper_is_executable_and_cwd_safe(tmp_path: Path) -> None:
    assert SCRIPT.exists()
    assert SCRIPT.stat().st_mode & 0o111
    syntax = subprocess.run(["bash", "-n", str(SCRIPT)], cwd=tmp_path, text=True, capture_output=True, check=False)
    assert syntax.returncode == 0, syntax.stderr
    result = subprocess.run(
        [str(SCRIPT), "--reports-root", str(tmp_path / "missing"), "--out-dir", str(tmp_path / "out"), "--json"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert '"unique_tests": 0' in result.stdout
