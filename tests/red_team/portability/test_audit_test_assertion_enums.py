# SCOPE: os-only
"""Paired portability proof for scripts/audit_test_assertion_enums.py.

Falsification probe: this audit is deliberately ROOT-RELATIVE — it scans the
tree named by ``--root`` (default: the process cwd) and reads its registry from
that same tree. The dangerous failure for a cwd-relative auditor is not a crash,
it is a SILENT GREEN: run from a directory that holds no registry and no tests,
report "no violations", exit 0, and let a caller read that as proof. This gate
exists precisely to stop tests from certifying a defect, so a gate that certifies
its own emptiness would be the same bug one level up.

The probes therefore pin the opposite of the usual cwd-invariance contract:

  * from a foreign cwd with no registry, the audit must FAIL LOUD (exit 2), not
    report a clean tree;
  * with an explicit ``--root``, the answer must be byte-identical no matter
    where the process was launched from, and must not leak the launch cwd.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/audit_test_assertion_enums.py"


def _run(cwd: Path, *args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, str(ARTIFACT), *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )


def test_help_succeeds_from_arbitrary_project_root(tmp_path: Path) -> None:
    result = _run(tmp_path, "--help")
    assert result.returncode == 0, result.stderr or result.stdout
    assert "usage" in result.stdout.lower(), result.stdout


def test_foreign_cwd_without_a_registry_fails_loud(tmp_path: Path) -> None:
    """The probe that matters: no registry must never read as "nothing wrong"."""
    result = _run(tmp_path)
    assert result.returncode == 2, (
        "an audit that cannot find its registry must exit 2, not report a clean "
        f"tree; got rc={result.returncode} stdout={result.stdout!r}"
    )
    assert "registry not found" in result.stderr, result.stderr
    assert "no test asserts" not in result.stdout, (
        "silent green from a foreign cwd: the audit claimed a verdict it did not earn"
    )


def test_explicit_root_is_cwd_invariant(tmp_path: Path) -> None:
    from_repo = _run(REPO_ROOT, "--root", str(REPO_ROOT), "--json")
    from_foreign = _run(tmp_path, "--root", str(REPO_ROOT), "--json")
    assert from_foreign.returncode == from_repo.returncode, from_foreign.stderr
    assert from_foreign.stdout == from_repo.stdout
    assert str(tmp_path) not in from_foreign.stdout
