"""Tests for scripts/invariant-check-helper.py — invariant proposal generator."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "scripts" / "invariant-check-helper.py"

# Make the helper's functions importable for unit-level tests.
import types  # noqa: E402

_mod = types.ModuleType("invariant_check_helper")
_mod.__file__ = str(HELPER)
# Register BEFORE exec so dataclass() can resolve the module via sys.modules.
sys.modules["invariant_check_helper"] = _mod
with open(HELPER, encoding="utf-8") as _fh:
    _code = _fh.read()
exec(compile(_code, str(HELPER), "exec"), _mod.__dict__)  # noqa: S102


# --------------------------------------------------------------------------- #
# Unit tests — individual functions                                            #
# --------------------------------------------------------------------------- #


def test_extract_python_finds_numeric_assignments(tmp_path: Path) -> None:
    py = tmp_path / "sample.py"
    py.write_text(
        "\n".join(
            [
                "_CPU_THRESHOLD_PCT = 5.0",
                "_HEARTBEAT_STALE_S = 900",
                "NAME = 'not-a-number'",
                "_SAMPLE_COUNT = 3",
            ]
        )
    )
    constants = _mod.extract_python(str(py))
    names = {c.name for c in constants}
    assert "_CPU_THRESHOLD_PCT" in names
    assert "_HEARTBEAT_STALE_S" in names
    assert "_SAMPLE_COUNT" in names
    assert "NAME" not in names  # non-numeric assignment skipped
    cpu = next(c for c in constants if c.name == "_CPU_THRESHOLD_PCT")
    assert cpu.value == 5.0


def test_similarity_pairs_by_stem() -> None:
    # Normalized suffix stripping: "_CPU_IDLE_THRESHOLD_PCT" ~ "cpu_idle_threshold"
    assert _mod.similarity("_CPU_IDLE_THRESHOLD_PCT", "cpu_idle_threshold") >= 0.75
    # Identical after normalization
    assert _mod.similarity("_SAMPLE_COUNT", "sample_count") == 1.0
    # Very different names score low
    assert _mod.similarity("foo_bar", "totally_unrelated_name") < 0.5


def test_pair_constants_respects_min_similarity(tmp_path: Path) -> None:
    py_file = tmp_path / "lib.py"
    py_file.write_text("_CPU_IDLE_THRESHOLD_PCT = 5.0\n_FOO_BAR = 42\n")
    adr_file = tmp_path / "adr.md"
    adr_file.write_text(
        "Threshold: `cpu_idle_threshold` = 5.0 %\n"
        "Sample count: `sample_count` = 3\n"
    )
    py_consts = _mod.extract_python(str(py_file))
    adr_consts = _mod.extract_adr(str(adr_file))
    pairs = _mod.pair_constants(py_consts, adr_consts, min_sim=0.5)
    assert pairs, "Expected at least one pair"
    # The CPU constant should find a match; _FOO_BAR should not.
    py_names = [p[0].name for p in pairs]
    assert "_CPU_IDLE_THRESHOLD_PCT" in py_names
    assert "_FOO_BAR" not in py_names


def test_emit_test_produces_valid_python_and_cites_adr() -> None:
    py_c = _mod.Constant(
        name="_CPU_THRESHOLD_PCT",
        value=5.0,
        source="py",
        line=10,
        file="lib/watchdog.py",
        raw="",
    )
    adr_c = _mod.Constant(
        name="cpu_threshold_pct",
        value=5.0,
        source="adr",
        line=42,
        file="docs/adrs/ADR-047-x.md",
        raw="",
    )
    text = _mod.emit_test(py_c, adr_c, adr_c.file)
    assert text.startswith("def test_"), text
    assert "ADR-047" in text
    assert "from lib.watchdog import _CPU_THRESHOLD_PCT" in text
    assert "ADR_VALUE = 5.0" in text
    assert "assert _CPU_THRESHOLD_PCT == ADR_VALUE" in text
    # Compiles as valid Python (function body). Wrap in exec context.
    compile(text, "<emit>", "exec")


def test_adr_id_preserves_leading_zeros() -> None:
    assert _mod.adr_id("docs/adrs/ADR-047-foo.md") == "047"
    assert _mod.adr_id("ADR-001-init.md") == "001"


def test_module_path_trims_absolute_prefix(tmp_path: Path) -> None:
    # Absolute path should resolve to a plausible dotted module based on anchor
    abs_path = "/Users/x/project/lib/session_watchdog_lib.py"
    mp = _mod.module_path(abs_path)
    assert mp == "lib.session_watchdog_lib"


# --------------------------------------------------------------------------- #
# End-to-end CLI tests                                                         #
# --------------------------------------------------------------------------- #


def test_cli_help_exits_zero() -> None:
    result = subprocess.run(
        ["python3", str(HELPER), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "invariant-check-helper" in result.stdout


def test_cli_produces_assertions_for_matching_pair(tmp_path: Path) -> None:
    py_file = tmp_path / "mod.py"
    py_file.write_text(
        "_CPU_IDLE_THRESHOLD_PCT = 5.0\n_SAMPLE_COUNT = 3\n"
    )
    adr_file = tmp_path / "ADR-099-fake.md"
    adr_file.write_text(
        "Invariant: `cpu_idle_threshold` = 5.0 %\n"
        "Invariant: `sample_count` = 3\n"
    )
    result = subprocess.run(
        ["python3", str(HELPER), str(adr_file), str(py_file)],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "def test_" in result.stdout
    assert "ADR-099" in result.stdout
    assert "ADR_VALUE" in result.stdout


def test_cli_emits_parseable_python(tmp_path: Path) -> None:
    """The assertions portion of the output must be syntactically valid Python.
    Run from tmp_path so relative paths yield clean identifiers."""
    py_file = tmp_path / "mymod.py"
    py_file.write_text("X = 10\n")
    adr_file = tmp_path / "ADR-010-z.md"
    adr_file.write_text("`x` = 10\n")
    result = subprocess.run(
        ["python3", str(HELPER), adr_file.name, py_file.name],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    # Strip comment-only preamble lines, compile the rest.
    body = "\n".join(
        ln for ln in result.stdout.splitlines() if not ln.startswith("#")
    )
    compile(body, "<cli>", "exec")


def test_cli_real_adr_047_pair_produces_non_empty_output() -> None:
    """Acceptance criterion: running on the real ADR-047 + session_watchdog_lib.py
    pair produces at least one proposed invariant."""
    adr = REPO_ROOT / "docs" / "adrs" / "ADR-047-session-lifecycle-management.md"
    lib = REPO_ROOT / "lib" / "session_watchdog_lib.py"
    if not adr.exists() or not lib.exists():
        pytest.skip("ADR-047 or session_watchdog_lib.py not present")
    result = subprocess.run(
        ["python3", str(HELPER), str(adr), str(lib)],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "def test_" in result.stdout, (
        f"Expected at least one proposed invariant, got:\n{result.stdout}"
    )
