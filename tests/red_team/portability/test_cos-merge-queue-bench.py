"""
Portability proofs for scripts/cos-merge-queue-bench.sh — P2.2 (ADR-116).

3 proofs:
1. Script is portable bash (shebang + set -euo pipefail)
2. Unknown options produce a non-zero exit and do not silently succeed
3. --help exits 0 and produces usage output
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCH_SH = REPO_ROOT / "scripts" / "cos-merge-queue-bench.sh"


def _run(args: list[str], env_extra: dict | None = None) -> subprocess.CompletedProcess:
    import os
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(BENCH_SH), *args],
        capture_output=True,
        text=True,
        env=env,
    )


class TestBenchShPortability:
    """cos-merge-queue-bench.sh is a portable bash script."""

    def test_script_exists_and_is_bash(self):
        """Script exists and has a bash shebang."""
        assert BENCH_SH.exists(), f"Missing: {BENCH_SH}"
        first_line = BENCH_SH.read_text().splitlines()[0]
        assert "bash" in first_line, f"Expected bash shebang, got: {first_line!r}"

    def test_script_has_strict_mode(self):
        """Script uses set -euo pipefail for safety."""
        content = BENCH_SH.read_text()
        assert "set -euo pipefail" in content, "Missing strict mode"


class TestBenchShUnknownOption:
    """Unknown options are rejected with a non-zero exit code."""

    def test_unknown_option_exits_nonzero(self):
        """Passing an unknown option returns exit code 1."""
        result = _run(["--not-a-real-option"])
        assert result.returncode != 0, (
            f"Expected non-zero exit for unknown option, got {result.returncode}"
        )
        assert "Unknown option" in result.stderr or "Unknown option" in result.stdout


class TestBenchShHelp:
    """--help exits 0 and produces usage output."""

    def test_help_exits_zero(self):
        """--help exits with code 0."""
        result = _run(["--help"])
        assert result.returncode == 0, (
            f"Expected exit 0 for --help, got {result.returncode}: {result.stderr}"
        )

    def test_help_shows_sessions_option(self):
        """--help output describes the --sessions option."""
        result = _run(["--help"])
        combined = result.stdout + result.stderr
        assert "--sessions" in combined, f"--help should mention --sessions, got: {combined[:300]}"
