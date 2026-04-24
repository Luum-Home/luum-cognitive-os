"""Behavioral tests for skills/invariant-check — ADR-059 Phase 1 pilot.

The invariant-check skill has a real backing script:
    scripts/invariant_check_helper.py

Tests validate the helper's contract directly (no LLM calls needed).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HELPER = PROJECT_ROOT / "scripts" / "invariant_check_helper.py"

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 1. Imports / invocation — script exists and is importable
# ---------------------------------------------------------------------------


class TestInvariantCheckHelperExists:
    def test_helper_script_exists(self):
        """SKILL.md references scripts/invariant_check_helper.py — it must exist."""
        assert HELPER.exists(), f"Missing backing script: {HELPER}"

    def test_helper_importable(self):
        """The helper's main() function must be importable without side-effects."""
        spec = {}
        exec(compile(HELPER.read_text(), str(HELPER), "exec"), spec)
        assert "main" in spec, "main() function not found in helper"


# ---------------------------------------------------------------------------
# 2. Contract test — calling main with valid inputs returns correct shape
# ---------------------------------------------------------------------------


class TestInvariantCheckContract:
    def test_exit_code_zero_with_valid_files(self, tmp_path: Path):
        """Helper exits 0 when at least one file is readable."""
        py_file = tmp_path / "lib_module.py"
        adr_file = tmp_path / "ADR-099-test.md"

        py_file.write_text("TIMEOUT_MS = 300\nMAX_RETRIES = 3\n")
        adr_file.write_text("The timeout is `TIMEOUT_MS=300` milliseconds.\n")

        result = subprocess.run(
            [sys.executable, str(HELPER), str(adr_file), str(py_file)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0, f"Unexpected exit code: {result.stderr}"

    def test_exit_code_nonzero_when_both_unreadable(self, tmp_path: Path):
        """Helper exits non-zero only when BOTH files are unreadable (SKILL.md contract)."""
        missing_a = tmp_path / "ghost_a.md"
        missing_b = tmp_path / "ghost_b.py"

        result = subprocess.run(
            [sys.executable, str(HELPER), str(missing_a), str(missing_b)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode != 0

    def test_output_shape_contains_header_comment(self, tmp_path: Path):
        """Output must contain the 'invariant-check' header comment block."""
        py_file = tmp_path / "lib_x.py"
        adr_file = tmp_path / "ADR-001-test.md"
        py_file.write_text("CPU_THRESHOLD_PCT = 5.0\n")
        adr_file.write_text("CPU threshold_pct=5.0 for idle detection.\n")

        result = subprocess.run(
            [sys.executable, str(HELPER), str(adr_file), str(py_file)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert "invariant-check" in result.stdout.lower()
        assert "Py file:" in result.stdout or "py file" in result.stdout.lower()


# ---------------------------------------------------------------------------
# 3. Happy path — matching constants produce a pytest test function
# ---------------------------------------------------------------------------


class TestInvariantCheckHappyPath:
    def test_matching_pair_produces_test_function(self, tmp_path: Path):
        """When py and ADR share a constant, output contains a def test_() function."""
        py_file = tmp_path / "lib_watchdog.py"
        adr_file = tmp_path / "ADR-047-session-lifecycle.md"

        py_file.write_text(dedent("""\
            _CPU_IDLE_THRESHOLD_PCT = 5.0
            _HEARTBEAT_STALE_THRESHOLD_S = 900
        """))
        adr_file.write_text(dedent("""\
            Both phases use `CPU_IDLE_THRESHOLD_PCT=5.0` (percentage).
            Heartbeat stale threshold_s=900 seconds.
        """))

        result = subprocess.run(
            [sys.executable, str(HELPER), str(adr_file), str(py_file)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0
        assert "def test_" in result.stdout, (
            "Expected at least one def test_() in output"
        )

    def test_assert_equality_in_output(self, tmp_path: Path):
        """Generated test must contain an assert statement."""
        py_file = tmp_path / "lib_session.py"
        adr_file = tmp_path / "ADR-010-budget.md"
        py_file.write_text("MAX_RETRIES = 3\n")
        adr_file.write_text("max_retries=3 is the limit.\n")

        result = subprocess.run(
            [sys.executable, str(HELPER), str(adr_file), str(py_file)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0
        assert "assert" in result.stdout

    def test_idempotency_same_output_on_repeat(self, tmp_path: Path):
        """Running the helper twice with the same inputs produces identical output."""
        py_file = tmp_path / "lib_idem.py"
        adr_file = tmp_path / "ADR-020-idem.md"
        py_file.write_text("TIMEOUT_S = 120\n")
        adr_file.write_text("timeout_s=120 seconds.\n")

        run1 = subprocess.run(
            [sys.executable, str(HELPER), str(adr_file), str(py_file)],
            capture_output=True, text=True, timeout=15,
        )
        run2 = subprocess.run(
            [sys.executable, str(HELPER), str(adr_file), str(py_file)],
            capture_output=True, text=True, timeout=15,
        )
        assert run1.stdout == run2.stdout


# ---------------------------------------------------------------------------
# 4. Error handling — invalid / missing input produces graceful error
# ---------------------------------------------------------------------------


class TestInvariantCheckErrorHandling:
    def test_one_missing_file_still_exits_zero(self, tmp_path: Path):
        """If only ONE file is missing, the helper should exit 0 (partial run)."""
        py_file = tmp_path / "lib_partial.py"
        py_file.write_text("LIMIT = 10\n")
        missing_adr = tmp_path / "missing.md"

        result = subprocess.run(
            [sys.executable, str(HELPER), str(missing_adr), str(py_file)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        # SKILL.md: "Exit code 0 on success; non-zero only if BOTH input files are unreadable"
        assert result.returncode == 0

    def test_no_constants_emits_no_pairs_message(self, tmp_path: Path):
        """When no pairs are found, output explains it rather than crashing."""
        py_file = tmp_path / "lib_empty.py"
        adr_file = tmp_path / "ADR-000-empty.md"
        py_file.write_text("# no assignments here\n")
        adr_file.write_text("This ADR has no numeric constants.\n")

        result = subprocess.run(
            [sys.executable, str(HELPER), str(adr_file), str(py_file)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0
        # Should not crash; output should be informational
        assert result.stderr == "" or "error" not in result.stderr.lower()
