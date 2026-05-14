from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
COS_INIT = REPO / "scripts" / "cos_init.py"


def test_cos_init_compiles_as_portable_bootstrap_surface() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(COS_INIT)],
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_cos_init_keeps_project_scope_filter_available() -> None:
    allowed = subprocess.run(
        [sys.executable, str(COS_INIT), "--internal-call", "scope_allows", "scripts/cos_init.py"],
        cwd=REPO,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    blocked = subprocess.run(
        [sys.executable, str(COS_INIT), "--internal-call", "scope_allows", "scripts/security_red_team.py"],
        cwd=REPO,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert allowed.returncode == 0, allowed.stderr
    assert blocked.returncode == 1
