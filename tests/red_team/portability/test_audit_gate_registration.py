# SCOPE: os-only
"""Paired portability proof for scripts/audit_gate_registration.py.

Falsification probe: the artifact resolves its own repo root from ``__file__``/
``BASH_SOURCE``, never from the process cwd. Running it from a foreign cwd must
produce byte-identical behaviour. An artifact that anchored on ``Path.cwd()``
fails this test instead of silently misbehaving in a consumer checkout.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / 'scripts/audit_gate_registration.py'


def _normalise(text: str) -> str:
    """Blank out volatile counters so only cwd-dependent drift can fail this.

    These audits print live telemetry columns (hook firing counts, byte sizes)
    that change between two consecutive runs *at the same cwd* -- verified, not
    assumed. Asserting them would make this proof flaky without making it
    stronger, so digits are masked while every path, name, verdict and column
    position stays under assertion.
    """
    return re.sub(r"\d+", "#", text)


def _run(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ARTIFACT)],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=25,
        check=False,
    )


def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """cwd-invariance: this audit takes no --help, so run it whole from both roots."""
    from_repo = _run(REPO_ROOT)
    from_foreign = _run(tmp_path)
    assert from_foreign.returncode == from_repo.returncode, from_foreign.stderr
    assert _normalise(from_foreign.stdout) == _normalise(from_repo.stdout)
    assert from_foreign.stdout.strip(), "audit produced no output from a foreign cwd"
