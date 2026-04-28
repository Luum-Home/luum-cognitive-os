"""Unit-level contract tests for scripts/pytest-with-summary.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.timeout(30)]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = PROJECT_ROOT / "scripts" / "pytest-with-summary.sh"


def _fake_pytest(tmp_path: Path) -> tuple[Path, Path]:
    capture = tmp_path / "captured-args.txt"
    fake = tmp_path / "fake-pytest.sh"
    fake.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$@" > "$CAPTURE_FILE"
while [ "$#" -gt 0 ]; do
  if [ "$1" = "--junitxml" ]; then
    shift
    printf '<testsuite tests="0"></testsuite>\n' > "$1"
  fi
  shift || true
done
echo '0 passed in 0.01s'
exit 0
"""
    )
    fake.chmod(0o755)
    return fake, capture


def _run_wrapper(
    tmp_path: Path,
    args: list[str],
    *,
    workers: str | None = "8",
) -> list[str]:
    fake, capture = _fake_pytest(tmp_path)
    env = {
        **os.environ,
        "PYTEST_BIN": str(fake),
        "CAPTURE_FILE": str(capture),
        "COS_TEST_REPORT_DIR": str(tmp_path / "reports"),
    }
    if workers is None:
        env.pop("COS_PYTEST_WORKERS", None)
    else:
        env["COS_PYTEST_WORKERS"] = workers
    result = subprocess.run(
        ["bash", str(WRAPPER), "--", *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return capture.read_text().splitlines()


@pytest.mark.parametrize(
    "explicit_args",
    [
        ["--numprocesses=4"],
        ["-n=4"],
        ["-n4"],
    ],
)
def test_explicit_xdist_worker_forms_prevent_adaptive_injection(
    tmp_path: Path,
    explicit_args: list[str],
) -> None:
    """ADR-068: every explicit xdist worker form wins over adaptive injection."""
    captured = _run_wrapper(tmp_path, [*explicit_args, "tests/unit/test_detect_runner_capacity.py", "-q"])

    assert explicit_args[0] in captured
    assert captured[:2] != ["-n", "8"], captured


def test_wrapper_injects_adaptive_workers_when_no_explicit_xdist_arg(tmp_path: Path) -> None:
    """Without an explicit xdist setting, the wrapper prepends the adaptive worker count."""
    captured = _run_wrapper(tmp_path, ["tests/unit/test_detect_runner_capacity.py", "-q"])

    assert captured[:2] == ["-n", "8"], captured


def test_stateful_broad_lane_defaults_to_serial_without_worker_override(tmp_path: Path) -> None:
    """Broad/stateful lanes must not become noisy xdist runs by accident."""
    captured = _run_wrapper(tmp_path, ["tests/", "-m", "not docker", "-q"], workers=None)

    assert captured[:2] != ["-n", "auto"], captured
    assert captured[:2] != ["-n", "8"], captured
    assert "tests/" in captured


def test_stateful_lane_still_respects_explicit_worker_override(tmp_path: Path) -> None:
    """Operators can still force parallelism when they intentionally want it."""
    captured = _run_wrapper(tmp_path, ["tests/", "-q"], workers="4")

    assert captured[:2] == ["-n", "4"], captured
