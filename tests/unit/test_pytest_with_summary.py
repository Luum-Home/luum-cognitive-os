"""Unit-level contract tests for scripts/pytest-with-summary.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.timeout(30)]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = PROJECT_ROOT / "scripts" / "pytest-with-summary.sh"


def _fake_pytest(tmp_path: Path, exit_code: int = 0) -> tuple[Path, Path]:
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
exit {exit_code}
""".format(exit_code=exit_code)
    )
    fake.chmod(0o755)
    return fake, capture


def _run_wrapper(
    tmp_path: Path,
    args: list[str],
    *,
    workers: str | None = "8",
    wrapper_args: list[str] | None = None,
    fake_exit_code: int = 0,
    expected_returncode: int = 0,
) -> tuple[list[str], Path]:
    fake, capture = _fake_pytest(tmp_path, exit_code=fake_exit_code)
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
        ["bash", str(WRAPPER), *(wrapper_args or []), "--", *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == expected_returncode, result.stdout + result.stderr
    return capture.read_text().splitlines(), Path(env["COS_TEST_REPORT_DIR"])


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
    captured, _reports = _run_wrapper(tmp_path, [*explicit_args, "tests/unit/test_detect_runner_capacity.py", "-q"])

    assert explicit_args[0] in captured
    assert captured[:2] != ["-n", "8"], captured


@pytest.mark.parametrize(
    ("wrapper_args", "expected_prefix"),
    [
        (["--workers", "0", "--lane", "unit"], []),
        (["--workers=4", "--lane=unit"], ["-n", "4"]),
    ],
)
def test_wrapper_worker_lane_scalars_bypass_adaptive_policy(
    tmp_path: Path,
    wrapper_args: list[str],
    expected_prefix: list[str],
) -> None:
    """cos-test passes scalar policy; wrapper must not infer lane/resource policy."""
    captured, _reports = _run_wrapper(
        tmp_path,
        ["tests/unit/test_detect_runner_capacity.py", "-q"],
        workers="8",
        wrapper_args=wrapper_args,
    )

    if expected_prefix:
        assert captured[:2] == expected_prefix, captured
    else:
        assert captured[:2] != ["-n", "8"], captured
        assert captured[:2] != ["-n", "auto"], captured


def test_wrapper_injects_adaptive_workers_when_no_explicit_xdist_arg(tmp_path: Path) -> None:
    """Without an explicit xdist setting, the wrapper prepends the adaptive worker count."""
    captured, _reports = _run_wrapper(tmp_path, ["tests/unit/test_detect_runner_capacity.py", "-q"])

    assert captured[:2] == ["-n", "8"], captured


def test_stateful_broad_lane_defaults_to_serial_without_worker_override(tmp_path: Path) -> None:
    """Broad/stateful lanes must not become noisy xdist runs by accident."""
    captured, _reports = _run_wrapper(tmp_path, ["tests/", "-m", "not docker", "-q"], workers=None)

    assert captured[:2] != ["-n", "auto"], captured
    assert captured[:2] != ["-n", "8"], captured
    assert "tests/" in captured


def test_stateful_lane_still_respects_explicit_worker_override(tmp_path: Path) -> None:
    """Operators can still force parallelism when they intentionally want it."""
    captured, _reports = _run_wrapper(tmp_path, ["tests/", "-q"], workers="4")

    assert captured[:2] == ["-n", "4"], captured


def test_wrapper_persists_resource_policy_metadata(tmp_path: Path) -> None:
    captured, reports = _run_wrapper(
        tmp_path,
        ["tests/unit/test_detect_runner_capacity.py", "-q"],
        wrapper_args=[
            "--workers",
            "0",
            "--lane",
            "unit",
            "--timeout-seconds",
            "180",
            "--docker-policy",
            "forbidden",
            "--cost-policy",
            "free_only",
            "--artifact-policy",
            "keep_summary",
        ],
    )

    assert captured[:2] != ["-n", "8"], captured
    metadata_path = reports / "latest" / "resource-policy.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata == {
        "artifact_policy": "keep_summary",
        "cost_policy": "free_only",
        "docker_policy": "forbidden",
        "lane": "unit",
        "outcome": "ok",
        "timeout_seconds": 180,
        "workers": "0",
    }
    summary = (reports / "latest" / "summary.txt").read_text(encoding="utf-8")
    assert "Resource outcome: ok" in summary
    assert "Docker policy: forbidden" in summary
    assert "Artifact policy: keep_summary" in summary


def test_wrapper_classifies_functional_failure_outcome(tmp_path: Path) -> None:
    _captured, reports = _run_wrapper(
        tmp_path,
        ["tests/unit/test_detect_runner_capacity.py", "-q"],
        wrapper_args=[
            "--workers",
            "0",
            "--lane",
            "unit",
            "--timeout-seconds",
            "180",
            "--docker-policy",
            "forbidden",
            "--cost-policy",
            "free_only",
            "--artifact-policy",
            "keep_summary",
        ],
        fake_exit_code=1,
        expected_returncode=1,
    )

    metadata_path = reports / "latest" / "resource-policy.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["outcome"] == "functional_failure"
    summary = (reports / "latest" / "summary.txt").read_text(encoding="utf-8")
    assert "Resource outcome: functional_failure" in summary
