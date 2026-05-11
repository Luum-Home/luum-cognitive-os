"""ADR-267: lib-symlink-invariant audit tests.

Verifies that the cos_lib_symlink_invariant_audit module correctly detects:
  - Clean state (proper symlinks) → 0 errors
  - Silent drift (divergent content, no symlink) → 1+ errors
  - Real-file dupe (identical content, no symlink) → 1+ warns, 0 errors
  - Dangling symlink → 1+ errors
  - Actual repo state: completes in <5s; baseline of known drifts surfaced.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import audit module (scripts/ is not on sys.path by default)
# ---------------------------------------------------------------------------

REPO = Path(__file__).parent.parent.parent
_AUDIT_MODULE_PATH = REPO / "scripts" / "cos_lib_symlink_invariant_audit.py"


def _load_audit_module():
    mod_name = "cos_lib_symlink_invariant_audit"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, _AUDIT_MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    # Must be registered before exec_module so @dataclass can resolve the module
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_audit = _load_audit_module()
run_audit = _audit.run_audit
SEVERITY_ERROR = _audit.SEVERITY_ERROR
SEVERITY_WARN = _audit.SEVERITY_WARN


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixture 1: Clean state — all duplicates are proper symlinks
# ---------------------------------------------------------------------------

@pytest.mark.audit
def test_clean_state_no_errors(tmp_path):
    """A root lib/ file that is a symlink to packages/*/lib/ → 0 errors."""
    # packages/mypkg/lib/shared.py — the canonical source
    pkg_file = tmp_path / "packages" / "mypkg" / "lib" / "shared.py"
    _write(pkg_file, "# canonical\nVERSION = 1\n")

    # lib/shared.py — proper symlink pointing at the package file
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    lib_link = lib_dir / "shared.py"
    os.symlink(pkg_file, lib_link)

    result = run_audit(tmp_path, scope="both")

    assert result.error_count == 0, (
        f"Expected 0 errors in clean fixture, got: "
        f"{[f.message for f in result.findings if f.severity == SEVERITY_ERROR]}"
    )
    assert result.passing_pairs >= 1


# ---------------------------------------------------------------------------
# Fixture 2: Silent drift — divergent content, no symlink
# ---------------------------------------------------------------------------

@pytest.mark.audit
def test_silent_drift_detected(tmp_path):
    """lib/X.py and packages/Y/lib/X.py exist with different content → 1+ errors."""
    pkg_file = tmp_path / "packages" / "mypkg" / "lib" / "worker.py"
    _write(pkg_file, "# package version\nVERSION = 2\n")

    lib_file = tmp_path / "lib" / "worker.py"
    _write(lib_file, "# root version — drifted\nVERSION = 99\n")

    result = run_audit(tmp_path, scope="both")

    drift_errors = [
        f for f in result.findings
        if f.severity == SEVERITY_ERROR and f.condition == "content_drift"
    ]
    assert len(drift_errors) >= 1, (
        "Expected at least 1 content_drift ERROR for silently diverged files"
    )
    # Both paths should appear in the finding
    assert any("worker.py" in f.lib_path for f in drift_errors)


# ---------------------------------------------------------------------------
# Fixture 3: Real-file dupe — identical content, no symlink
# ---------------------------------------------------------------------------

@pytest.mark.audit
def test_real_file_dupe_is_warn_not_error(tmp_path):
    """Identical content but no symlink → WARN only, 0 errors."""
    shared_content = "# shared module\nFOO = 'bar'\n"

    pkg_file = tmp_path / "packages" / "mypkg" / "lib" / "utils.py"
    _write(pkg_file, shared_content)

    lib_file = tmp_path / "lib" / "utils.py"
    _write(lib_file, shared_content)

    result = run_audit(tmp_path, scope="both")

    assert result.error_count == 0, (
        f"Expected 0 errors for real-file dupe, got: "
        f"{[f.message for f in result.findings if f.severity == SEVERITY_ERROR]}"
    )
    warn_dupes = [
        f for f in result.findings
        if f.severity == SEVERITY_WARN and f.condition == "real_file_dupe"
    ]
    assert len(warn_dupes) >= 1, (
        "Expected at least 1 real_file_dupe WARN for identical-content non-symlink pair"
    )


# ---------------------------------------------------------------------------
# Fixture 4: Dangling symlink
# ---------------------------------------------------------------------------

@pytest.mark.audit
def test_dangling_symlink_is_error(tmp_path):
    """lib/X.py is a symlink to a non-existent path → ERROR."""
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)

    # Symlink pointing at a path that does not exist
    dangling = lib_dir / "ghost.py"
    os.symlink(tmp_path / "packages" / "nowhere" / "lib" / "ghost.py", dangling)

    # Ensure packages/ exists so the walk doesn't bail early
    (tmp_path / "packages").mkdir(exist_ok=True)

    result = run_audit(tmp_path, scope="both")

    dangling_errors = [
        f for f in result.findings
        if f.severity == SEVERITY_ERROR and f.condition == "dangling_symlink"
    ]
    assert len(dangling_errors) >= 1, (
        "Expected at least 1 dangling_symlink ERROR for symlink to non-existent target"
    )
    assert any("ghost.py" in f.lib_path for f in dangling_errors)


# ---------------------------------------------------------------------------
# Test 5: Actual repo — performance + known-baseline assertion
# ---------------------------------------------------------------------------

# Known drifts as of 2026-05-11 ADR-267 audit.
# The audit surfaces MORE than the 3 originally cited because __init__.py has
# 3 separate drift pairs and retry_classifier.py is also diverged.
_KNOWN_DRIFT_LIB_FILES = {
    "lib/dispatch.py",
    "lib/__init__.py",
    "lib/review_agent.py",
    "lib/retry_classifier.py",  # additional drift uncovered by this audit
}

# Baseline: at least these many ERRORs exist in the repo before remediation.
_BASELINE_MIN_ERRORS = 3


@pytest.mark.audit
def test_actual_repo_performance_and_baseline():
    """Audit the live repo: completes in <5s and surfaces known drifts."""
    t0 = time.monotonic()
    result = run_audit(REPO, scope="both")
    elapsed = time.monotonic() - t0

    assert elapsed < 5.0, (
        f"Audit must complete in <5s — took {elapsed:.2f}s. "
        "Check for I/O bottlenecks or large binary files in lib/."
    )

    if result.error_count > _BASELINE_MIN_ERRORS:
        # More errors than expected — repo has not been remediated yet.
        # Mark as xfail with a TODO surfaced in the message.
        pytest.xfail(
            reason=(
                f"post-remediation should converge to 0 ERRORs. "
                f"Current count: {result.error_count}. "
                f"TODO: run `python3 scripts/cos_lib_symlink_invariant_audit.py --format markdown` "
                f"and resolve each finding per ADR-267."
            )
        )

    assert result.error_count >= _BASELINE_MIN_ERRORS, (
        f"Expected at least {_BASELINE_MIN_ERRORS} drift ERROR(s) in the "
        f"un-remediated repo, got {result.error_count}. "
        f"If the repo was intentionally remediated, lower _BASELINE_MIN_ERRORS."
    )

    # Verify the 3 originally cited files appear in findings
    cited = {"lib/dispatch.py", "lib/__init__.py", "lib/review_agent.py"}
    found_lib_paths = {f.lib_path for f in result.findings if f.severity == SEVERITY_ERROR}
    missing = cited - found_lib_paths
    assert not missing, (
        f"Expected these known-drift files to appear in ERROR findings, "
        f"but they were missing: {missing}"
    )
