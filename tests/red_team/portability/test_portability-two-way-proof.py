# SCOPE: os-only
"""Paired portability proof for scripts/portability-two-way-proof.sh.

Falsification probe: the artifact resolves its own repo root from ``__file__``/
``BASH_SOURCE``, never from the process cwd. Running it from a foreign cwd must
produce the same behaviour. An artifact anchored on ``Path.cwd()`` fails this
test instead of silently misbehaving in a consumer checkout.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# La direccion GNU de este artefacto levanta un contenedor. Este proof pareado
# mide cwd-invarianza, no portabilidad, y lo corre tres veces: pagar tres pulls
# lo haria timeout. El SKIP es explicito en la salida del propio script, asi que
# la aserto de igualdad sigue viendo todo lo demas.
_ENV = {**os.environ, "COS_PROOF_SKIP_LINUX": "1"}


REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / 'scripts/portability-two-way-proof.sh'


def _normalise(text: str) -> str:
    """Blank out volatile counters so only cwd-dependent drift can fail this.

    The scaffold's probe found this artifact's output stable across two
    consecutive runs, but the output carries digits and a two-second probe
    cannot prove a counter will not advance between this proof's two runs. The
    mask is the conservative reading of an undersampled measurement.

    Asserting those digits would make this proof flaky without making it
    stronger, so they are masked while every path, name, verdict and column
    position stays under assertion.
    """
    return re.sub(r"\d+", "#", text)


def _run(cwd: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        ["bash", str(ARTIFACT)],
        cwd=str(cwd),
        env=_ENV,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )


def test_runs_whole_from_arbitrary_project_root(tmp_path: Path) -> None:
    """This artifact has no `--help` contract, so it is run whole and must speak."""
    result = _run(tmp_path)
    assert result.stdout.strip(), result.stderr or "artifact produced no output from a foreign cwd"


def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """cwd-invariance: same exit code and same output from repo root and elsewhere."""
    from_repo = _run(REPO_ROOT)
    from_foreign = _run(tmp_path)
    assert from_foreign.returncode == from_repo.returncode, from_foreign.stderr
    assert _normalise(from_foreign.stdout) == _normalise(from_repo.stdout)
    assert str(tmp_path) not in from_foreign.stdout
