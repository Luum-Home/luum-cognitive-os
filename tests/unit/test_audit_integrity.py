"""Behavioral tests for skills/audit-integrity — ADR-059 Phase 1 pilot.

audit-integrity relies on hooks/_lib/file_checker.sh for symlink-aware checks.
Tests validate the shell library's functions (no LLM calls needed).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FILE_CHECKER = PROJECT_ROOT / "hooks" / "_lib" / "file_checker.sh"

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 1. Imports / invocation — backing library exists
# ---------------------------------------------------------------------------


class TestAuditIntegrityLibraryExists:
    def test_file_checker_exists(self):
        """SKILL.md instructs sourcing hooks/_lib/file_checker.sh — it must exist."""
        assert FILE_CHECKER.exists(), f"Missing file_checker.sh: {FILE_CHECKER}"

    def test_file_checker_has_required_functions(self):
        """file_checker.sh must define the 4 functions the skill uses."""
        content = FILE_CHECKER.read_text()
        required = [
            "file_exists()",
            "file_exists_strict()",
            "resolve_path()",
            "is_broken_symlink()",
        ]
        for fn in required:
            assert fn in content, f"Missing function definition: {fn}"

    def test_skill_md_exists(self):
        """skills/audit-integrity/SKILL.md must be present and non-empty."""
        skill_md = PROJECT_ROOT / "skills" / "audit-integrity" / "SKILL.md"
        assert skill_md.exists()
        assert skill_md.stat().st_size > 100


# ---------------------------------------------------------------------------
# 2. Contract test — file_exists() behavior
# ---------------------------------------------------------------------------


class TestFileCheckerContract:
    def _run_checker(self, script: str, tmp_path: Path) -> subprocess.CompletedProcess:
        bash_script = f"""
set -e
source {FILE_CHECKER}
{script}
"""
        return subprocess.run(
            ["bash", "-c", bash_script],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            timeout=10,
        )

    def test_file_exists_returns_true_for_real_file(self, tmp_path: Path):
        """file_exists() must return 0 (truthy) for a real file."""
        real_file = tmp_path / "real.txt"
        real_file.write_text("content")

        result = self._run_checker(
            f'file_exists "{real_file}" && echo "YES" || echo "NO"',
            tmp_path,
        )
        assert result.returncode == 0
        assert "YES" in result.stdout

    def test_file_exists_returns_false_for_missing_file(self, tmp_path: Path):
        """file_exists() must return 1 (falsy) for a non-existent path."""
        missing = tmp_path / "ghost.txt"

        result = self._run_checker(
            f'file_exists "{missing}" && echo "YES" || echo "NO"',
            tmp_path,
        )
        assert "NO" in result.stdout

    def test_file_exists_returns_true_for_symlink(self, tmp_path: Path):
        """file_exists() must return 0 for a symlink (even with valid target)."""
        real_file = tmp_path / "target.txt"
        real_file.write_text("target")
        symlink = tmp_path / "link.txt"
        symlink.symlink_to(real_file)

        result = self._run_checker(
            f'file_exists "{symlink}" && echo "YES" || echo "NO"',
            tmp_path,
        )
        assert "YES" in result.stdout


# ---------------------------------------------------------------------------
# 3. Happy path — is_broken_symlink correctly identifies broken links
# ---------------------------------------------------------------------------


class TestAuditIntegrityHappyPath:
    def _run_checker(self, script: str, tmp_path: Path) -> subprocess.CompletedProcess:
        bash_script = f"""
set -e
source {FILE_CHECKER}
{script}
"""
        return subprocess.run(
            ["bash", "-c", bash_script],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            timeout=10,
        )

    def test_is_broken_symlink_detects_broken_link(self, tmp_path: Path):
        """is_broken_symlink() must return 0 for a symlink pointing to a missing target."""
        symlink = tmp_path / "broken_link.sh"
        symlink.symlink_to(tmp_path / "does_not_exist.sh")

        result = self._run_checker(
            f'is_broken_symlink "{symlink}" && echo "BROKEN" || echo "OK"',
            tmp_path,
        )
        assert "BROKEN" in result.stdout

    def test_is_broken_symlink_returns_false_for_valid_symlink(self, tmp_path: Path):
        """is_broken_symlink() must return 1 for a valid symlink."""
        target = tmp_path / "real_hook.sh"
        target.write_text("#!/bin/bash\n")
        symlink = tmp_path / "valid_link.sh"
        symlink.symlink_to(target)

        result = self._run_checker(
            f'is_broken_symlink "{symlink}" && echo "BROKEN" || echo "OK"',
            tmp_path,
        )
        assert "OK" in result.stdout

    def test_resolve_path_returns_canonical_path(self, tmp_path: Path):
        """resolve_path() must return the real path of a symlink."""
        target = tmp_path / "canonical.sh"
        target.write_text("#!/bin/bash\n")
        link = tmp_path / "alias.sh"
        link.symlink_to(target)

        result = self._run_checker(
            f'resolved=$(resolve_path "{link}"); echo "$resolved"',
            tmp_path,
        )
        assert result.returncode == 0
        resolved = result.stdout.strip()
        assert resolved == str(target.resolve()), (
            f"Expected {target.resolve()}, got {resolved}"
        )


# ---------------------------------------------------------------------------
# 4. Error handling — sourcing the library must not crash in isolation
# ---------------------------------------------------------------------------


class TestAuditIntegrityErrorHandling:
    def test_sourcing_file_checker_does_not_crash(self, tmp_path: Path):
        """Sourcing file_checker.sh with no arguments must exit 0."""
        result = subprocess.run(
            ["bash", "-c", f"source {FILE_CHECKER}; echo 'OK'"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "OK" in result.stdout

    def test_file_exists_strict_returns_false_for_broken_symlink(self, tmp_path: Path):
        """file_exists_strict() must return 1 for a symlink with a missing target."""
        broken_link = tmp_path / "strict_test.sh"
        broken_link.symlink_to(tmp_path / "nonexistent_target.sh")

        result = subprocess.run(
            ["bash", "-c",
             f"source {FILE_CHECKER}; "
             f'file_exists_strict "{broken_link}" && echo "EXISTS" || echo "MISSING"'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert "MISSING" in result.stdout
