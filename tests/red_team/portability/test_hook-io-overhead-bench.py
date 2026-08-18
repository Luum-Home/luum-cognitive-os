# SCOPE: os-only
"""Paired portability proof for scripts/hook-io-overhead-bench.sh.

Scope of this proof, stated plainly so nobody reads more into it than it earns:

The artifact is a wall-clock benchmark whose own header says it is deliberately
NOT wired into CI, because any threshold stable on a loaded machine is too loose
to catch the regression it exists for. Measured here: one iteration costs ~15 s
wall for ~1.3 s CPU on a loaded machine. Running it twice to compare output
would blow the 30 s suite timeout and abort the whole pytest session -- so this
proof does NOT assert its numbers and does NOT run it to completion.

What it DOES prove, and what makes it falsifiable: the script resolves the repo
it benchmarks from ``BASH_SOURCE``, not from the caller's cwd. It is started
from a foreign project root and must reach its first report header. A version
that anchored on ``Path.cwd()``/``$PWD`` would die on its ``-d`` guards before
printing anything, and this test would fail.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/hook-io-overhead-bench.sh"
FIRST_HEADER = "PART A"


def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    process = subprocess.Popen(
        ["bash", str(ARTIFACT), "1"],
        cwd=str(tmp_path),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    try:
        header = None
        assert process.stdout is not None
        for line in process.stdout:
            if FIRST_HEADER in line:
                header = line
                break
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            process.kill()
            process.wait(timeout=10)

    assert header is not None, "benchmark never reached its first header from a foreign cwd"
    assert str(tmp_path) not in header
