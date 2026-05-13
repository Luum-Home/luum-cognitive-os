#!/usr/bin/env python3
# SCOPE: os-only
"""Behavioral tests for check_test_quality.py scope isolation.

These tests verify that the script:
  1. BLOCKS when given an explicit file list containing structural-only assertions.
  2. Does NOT block when those same files are only in the working tree
     (not passed as arguments) — i.e., working-tree-only files are invisible.
  3. Returns 0 (no-op) when invoked with no arguments and no mode flag.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "check_test_quality.py"


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


@pytest.fixture()
def structural_only_test_file(tmp_path: Path) -> Path:
    """Create a temp file containing only structural assertions."""
    f = tmp_path / "tests" / "unit" / "test_structural_dummy.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(
        textwrap.dedent("""\
            from pathlib import Path

            def test_file_exists():
                assert Path("/tmp").exists()

            def test_is_directory():
                assert Path("/tmp").is_dir()

            def test_membership_check():
                data = {"key": "value"}
                assert "key" in data
        """),
        encoding="utf-8",
    )
    return f


@pytest.fixture()
def behavioral_test_file(tmp_path: Path) -> Path:
    """Create a temp file with at least one behavioral assertion."""
    f = tmp_path / "tests" / "unit" / "test_behavioral_dummy.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(
        textwrap.dedent("""\
            def test_addition_returns_correct_value():
                result = 1 + 1
                assert result == 2

            def test_list_append_side_effect():
                items: list[int] = []
                items.append(42)
                assert items == [42]
        """),
        encoding="utf-8",
    )
    return f


class TestExplicitFileListBlocks:
    """Script BLOCKS when given an explicit structural-only file."""

    def test_blocks_structural_only_file_passed_explicitly(self, structural_only_test_file: Path) -> None:
        """Passing a structural-only file as a positional arg must exit 1."""
        result = _run([str(structural_only_test_file)])
        assert result.returncode == 1, (
            f"Expected exit 1 (BLOCKED) for structural-only file, got {result.returncode}.\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )
        assert "BLOCKED" in result.stdout or "BLOCKED" in result.stderr

    def test_passes_behavioral_file_passed_explicitly(self, behavioral_test_file: Path) -> None:
        """Passing a behavioral file as a positional arg must exit 0."""
        result = _run([str(behavioral_test_file)])
        assert result.returncode == 0, (
            f"Expected exit 0 for behavioral file, got {result.returncode}.\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )


class TestWorkingTreeIsolation:
    """Untracked/working-tree-only files must NOT trigger a block."""

    def test_structural_file_not_in_arg_list_does_not_block(self, structural_only_test_file: Path) -> None:
        """When the structural file exists on disk but is NOT passed as an arg,
        the script must exit 0 — working tree is NOT scanned by default."""
        # Run from inside tmp_path so the file is in the working tree,
        # but pass NO positional args (and no --working-tree flag).
        result = _run([], cwd=structural_only_test_file.parent.parent.parent)
        assert result.returncode == 0, (
            f"Expected exit 0 when no args given (no-op mode), got {result.returncode}.\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )
        # Must NOT output a BLOCKED line
        combined = result.stdout + result.stderr
        assert "BLOCKED" not in combined, (
            "Script emitted BLOCKED for a file that was NOT passed as an argument."
        )

    def test_no_args_no_mode_is_noop(self, tmp_path: Path) -> None:
        """Invoking with no args and no mode flag must exit 0 with an informative message."""
        result = _run([], cwd=tmp_path)
        assert result.returncode == 0, (
            f"Expected exit 0 for no-args invocation, got {result.returncode}.\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )


class TestWorkingTreeFlagOptIn:
    """--working-tree flag enables the opt-in whole-tree scan."""

    def test_working_tree_flag_scans_structurally_when_requested(self, structural_only_test_file: Path, tmp_path: Path) -> None:
        """--working-tree must scan and find the structural file when invoked from its parent."""
        # The structural_only_test_file lives at tmp_path/tests/unit/...
        result = _run(["--working-tree"], cwd=tmp_path)
        # Should detect structural-only content and exit 1
        assert result.returncode == 1, (
            f"Expected --working-tree to block on structural file, got {result.returncode}.\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )
        assert "BLOCKED" in result.stdout or "BLOCKED" in result.stderr


class TestLegacyPreCommitMode:
    """--pre-commit mode still exists for backwards compatibility."""

    def test_pre_commit_flag_is_accepted(self) -> None:
        """--pre-commit must not raise an error (even if no files are staged)."""
        result = _run(["--pre-commit"])
        # With nothing staged, it should exit 0 cleanly
        assert result.returncode == 0, (
            f"--pre-commit with no staged files should exit 0, got {result.returncode}.\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )
