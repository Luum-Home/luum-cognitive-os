"""Contract tests for hooks/global-verify.sh — ADR-027 Phase 1."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parents[2]
HOOK = PROJECT_DIR / "hooks" / "global-verify.sh"
RESOLVER_PATH = PROJECT_DIR / "lib" / "targeted_test_resolver.py"


def run_hook(mode: str, agent_id: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    """Run global-verify.sh with the given mode and agent_id."""
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(PROJECT_DIR)
    env["AGENT_ID"] = agent_id
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK), mode],
        capture_output=True,
        text=True,
        env=env,
    )


class _FakeResolver:
    """Context manager that temporarily installs a fake targeted_test_resolver.py."""

    def __init__(self, test_ids: list[str]):
        self._test_ids = test_ids
        self._existed = RESOLVER_PATH.exists()
        self._original: bytes | None = None

    def __enter__(self):
        if self._existed:
            self._original = RESOLVER_PATH.read_bytes()
        code = "def resolve_tests_for_changes(files):\n    return " + repr(self._test_ids) + "\n"
        RESOLVER_PATH.write_text(code, encoding="utf-8")
        return self

    def __exit__(self, *_):
        if self._existed and self._original is not None:
            RESOLVER_PATH.write_bytes(self._original)
        elif not self._existed:
            RESOLVER_PATH.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test 1: before-phase writes skipped marker when no tests resolve
# ---------------------------------------------------------------------------


def test_before_phase_writes_skipped_marker_when_no_tests_resolve(tmp_path):
    """Before phase writes a skipped JSON marker when the resolver returns no tests."""
    agent_id = "test-skip-marker"
    baseline_dir = PROJECT_DIR / ".cognitive-os" / "runtime" / "verify-baseline"
    baseline_file = baseline_dir / f"{agent_id}.json"

    # Ensure no leftover baseline from a prior run
    baseline_file.unlink(missing_ok=True)

    with _FakeResolver([]):
        try:
            result = run_hook("before", agent_id)
            # Hook should exit 0 (safe skip)
            assert result.returncode == 0, f"Expected exit 0, got {result.returncode}.\nstderr: {result.stderr}"
            # Baseline file must exist
            assert baseline_file.exists(), f"Expected baseline file at {baseline_file}"
            data = json.loads(baseline_file.read_text())
            assert data.get("skipped") is True, f"Expected skipped=True, got: {data}"
            assert "reason" in data
        finally:
            baseline_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test 2: before-phase writes baseline when tests resolve
# ---------------------------------------------------------------------------


def test_before_phase_writes_baseline_when_tests_resolve(tmp_path):
    """Before phase writes a baseline JSON with passed/failed counts when tests resolve."""
    agent_id = "test-baseline-write"
    baseline_dir = PROJECT_DIR / ".cognitive-os" / "runtime" / "verify-baseline"
    baseline_file = baseline_dir / f"{agent_id}.json"

    # Clean up any leftover
    baseline_file.unlink(missing_ok=True)

    # Use a real existing lightweight test so pytest actually resolves it.
    existing_test = str(PROJECT_DIR / "tests" / "contracts" / "test_process_registry.py")

    with _FakeResolver([existing_test]):
        try:
            result = run_hook("before", agent_id)
            # Hook should exit 0 regardless of test results (baseline capture, not blocking)
            assert result.returncode == 0, f"Expected exit 0.\nstderr: {result.stderr}\nstdout: {result.stdout}"
            assert baseline_file.exists(), f"Expected baseline file at {baseline_file}"
            data = json.loads(baseline_file.read_text())
            assert "baseline" in data, f"Expected 'baseline' key in {data}"
            baseline = data["baseline"]
            assert "test_count" in baseline
            assert baseline["test_count"] >= 1
        finally:
            baseline_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test 3: after-phase computes delta, exits 0 for no regression, 1 for regression
# ---------------------------------------------------------------------------


def test_after_phase_no_regression_exits_0(tmp_path):
    """After phase exits 0 when test results are equal or improved."""
    agent_id = "test-after-no-regression"
    baseline_dir = PROJECT_DIR / ".cognitive-os" / "runtime" / "verify-baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    baseline_file = baseline_dir / f"{agent_id}.json"

    # Write a fake passing test
    fake_test = tmp_path / "test_passing.py"
    fake_test.write_text("def test_ok():\n    assert True\n")
    test_path = str(fake_test)

    # Baseline: 1 passed, 0 failed
    baseline_data = {
        "baseline": {
            "test_count": 1,
            "passed": 1,
            "failed": 0,
            "returncode": 0,
            "tests": [test_path],
            "fingerprint": "abc123",
        },
        "files": ["some_file.py"],
        "mode": "before",
    }
    baseline_file.write_text(json.dumps(baseline_data), encoding="utf-8")

    with _FakeResolver([test_path]):
        try:
            result = run_hook("after", agent_id)
            # Passing test → 1 passed, 0 failed → delta_failed=0 → exit 0
            assert result.returncode == 0, (
                f"Expected exit 0 (no regression).\nstderr: {result.stderr}\nstdout: {result.stdout}"
            )
            assert not baseline_file.exists(), "Baseline file should be removed after 'after' phase"
        finally:
            baseline_file.unlink(missing_ok=True)


def test_after_phase_regression_exits_1(tmp_path):
    """After phase exits 1 when the current run has more failures than the baseline."""
    agent_id = "test-after-regression"
    baseline_dir = PROJECT_DIR / ".cognitive-os" / "runtime" / "verify-baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    baseline_file = baseline_dir / f"{agent_id}.json"

    # Write a fake test that FAILS
    fake_test = tmp_path / "fake_test.py"
    fake_test.write_text(
        "def test_fail():\n    assert False, 'intentional regression'\n"
    )
    test_path = str(fake_test)

    # Baseline claims 5 passed, 0 failed — current will have 0 passed, 1 failed
    baseline_data = {
        "baseline": {
            "test_count": 1,
            "passed": 5,
            "failed": 0,
            "returncode": 0,
            "tests": [test_path],
            "fingerprint": "xyz789",
        },
        "files": ["some_file.py"],
        "mode": "before",
    }
    baseline_file.write_text(json.dumps(baseline_data), encoding="utf-8")

    with _FakeResolver([test_path]):
        try:
            result = run_hook("after", agent_id)
            # Baseline had 0 failures, fake_test has 1 failure → delta_failed = 1 > 0 → exit 1
            assert result.returncode == 1, (
                f"Expected exit 1 (regression detected), got {result.returncode}.\n"
                f"stderr: {result.stderr}\nstdout: {result.stdout}"
            )
            assert "BLOCKER" in result.stderr, f"Expected BLOCKER in stderr, got: {result.stderr}"
            assert not baseline_file.exists(), "Baseline file should be removed after 'after' phase"
        finally:
            baseline_file.unlink(missing_ok=True)
