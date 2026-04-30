"""
Regression test for cos-test worker flag bug (2026-04-30).

Bug: cos-test cluster passed --workers 0 to pytest-with-summary.sh for the
unit lane even though test-lanes.yaml declares parallel: true. Root cause was
test-resource-policy.yaml having workers: 0 for the unit lane.

Fix: test-resource-policy.yaml unit lane changed from workers: 0 to
workers: auto so the resource policy no longer overrides parallel execution.

These tests capture the --dry-run output and assert the correct --workers
flag is present, providing a fast (<1s) regression guard that does not
require actually running pytest.
"""

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

# Path to the cos-test binary (built at repo root for convenience).
REPO_ROOT = Path(__file__).parent.parent.parent
COS_TEST_BINARY = REPO_ROOT / "cos-test"


def _cos_test_available() -> bool:
    return COS_TEST_BINARY.is_file()


@pytest.fixture(scope="module")
def require_cos_test_binary():
    """Skip all tests in this module if cos-test binary is not built."""
    if not _cos_test_available():
        pytest.skip(
            f"cos-test binary not found at {COS_TEST_BINARY}. "
            "Build with: cd cmd/cos-test && go build -o ../../cos-test ."
        )


def _run_dry_run(lane: str) -> str:
    """Run cos-test cluster --lane <lane> --dry-run and return stdout."""
    result = subprocess.run(
        [str(COS_TEST_BINARY), "cluster", "--lane", lane, "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    # dry-run always exits 0; we just care about stdout
    return result.stdout


class TestCosTestWorkersFlag:
    """Regression guards for AC2/AC4/AC5 of test-runner-ergonomics-proposal."""

    def test_unit_lane_passes_workers_auto(self, require_cos_test_binary):
        """cos-test cluster --lane unit must pass --workers auto (not --workers 0).

        Regression guard: before fix, test-resource-policy.yaml had workers: 0
        for the unit lane which caused serial execution despite parallel: true.
        """
        output = _run_dry_run("unit")
        assert "--workers auto" in output, (
            f"unit lane (parallel:true) should pass --workers auto, "
            f"but dry-run output was:\n{output}"
        )
        assert "--workers 0" not in output, (
            f"unit lane must NOT pass --workers 0 (serial regression), "
            f"but dry-run output was:\n{output}"
        )

    def test_audit_lane_passes_workers_zero(self, require_cos_test_binary):
        """cos-test cluster --lane audit must pass --workers 0 (serial, no regression).

        audit lane has parallel: false due to shared install-touching state.
        """
        output = _run_dry_run("audit")
        assert "--workers 0" in output, (
            f"audit lane (parallel:false) must remain serial with --workers 0, "
            f"but dry-run output was:\n{output}"
        )
        assert "--workers auto" not in output, (
            f"audit lane must NOT pass --workers auto (would cause install flakes), "
            f"but dry-run output was:\n{output}"
        )

    def test_unit_lane_banner_shows_parallel(self, require_cos_test_binary):
        """Banner for unit lane must show 'parallel-safe' workers description."""
        output = _run_dry_run("unit")
        assert "parallel-safe" in output, (
            f"unit lane banner should describe workers as parallel-safe, got:\n{output}"
        )

    def test_audit_lane_banner_shows_serial(self, require_cos_test_binary):
        """Banner for audit lane must show 'serial' workers description."""
        output = _run_dry_run("audit")
        # The banner prints workers=serial (stateful) for parallel:false lanes
        assert "serial" in output, (
            f"audit lane banner should describe workers as serial, got:\n{output}"
        )
