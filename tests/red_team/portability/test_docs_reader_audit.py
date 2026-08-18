# SCOPE: os-only
"""Paired portability proof for scripts/docs_reader_audit.py.

Falsification probe: the artifact resolves its own repo root from ``__file__``/
``BASH_SOURCE``, never from the process cwd. Running it from a foreign cwd must
produce byte-identical behaviour. An artifact that anchored on ``Path.cwd()``
fails this test instead of silently misbehaving in a consumer checkout.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / 'scripts/docs_reader_audit.py'


def _run(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ARTIFACT), "--help"],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=25,
        check=False,
    )


def test_help_succeeds_from_arbitrary_project_root(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "usage" in result.stdout.lower(), result.stdout


def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """cwd-invariance: identical exit code and stdout from repo root and elsewhere."""
    from_repo = _run(REPO_ROOT)
    from_foreign = _run(tmp_path)
    assert from_foreign.returncode == from_repo.returncode
    assert from_foreign.stdout == from_repo.stdout
    assert str(tmp_path) not in from_foreign.stdout
