"""
tests/unit/test_capacity_logging.py

Unit tests for ADR-068 Phase 2 — capacity decision logging.

Verifies that pytest-with-summary.sh writes a valid capacity.json under
.cognitive-os/metrics/test-runs/<timestamp>/ on every run.

Tests:
  1. A real run produces capacity.json under the metrics dir.
  2. The JSON contains all required ADR-068 keys.
  3. When COS_PYTEST_WORKERS=8, workers_chosen and rule_fired reflect the override.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "pytest-with-summary.sh"

# ADR-068 Phase 2 required keys in capacity.json
REQUIRED_KEYS = {
    "timestamp_utc",
    "cores",
    "load_pct",
    "mem_available_gb",
    "battery_pct",
    "ci",
    "workers_chosen",
    "rule_fired",
    "pytest_args_inferred",
    "session_id",
    "junit_xml_path",
}


def _run_pytest_with_summary(
    tmp_path: Path,
    extra_env: dict[str, str] | None = None,
    extra_args: list[str] | None = None,
) -> tuple[int, Path]:
    """
    Run pytest-with-summary.sh targeting a tiny test file.

    Returns (exit_code, metrics_dir) where metrics_dir is the
    .cognitive-os/metrics/test-runs/<timestamp>/ directory written
    during the run.

    Uses isolated COS_TEST_REPORT_DIR and COS_METRICS_DIR under tmp_path
    so tests don't pollute the real repo directories.
    """
    report_dir = tmp_path / "reports"
    metrics_dir = tmp_path / "metrics"
    report_dir.mkdir()
    metrics_dir.mkdir()

    # A trivial test file that always passes immediately.
    test_file = tmp_path / "test_trivial.py"
    test_file.write_text(
        "import pytest\npytestmark = pytest.mark.unit\n\ndef test_pass():\n    assert True\n"
    )

    env = os.environ.copy()
    env["COS_TEST_REPORT_DIR"] = str(report_dir)
    env["COS_METRICS_DIR"] = str(metrics_dir)
    env["COGNITIVE_OS_SESSION_ID"] = "test-session-abc123"
    # Override workers detection to a stable value so tests are deterministic.
    env.setdefault("COS_PYTEST_WORKERS", "0")  # serial by default unless overridden
    if extra_env:
        env.update(extra_env)

    args = extra_args or []
    cmd = ["bash", str(SCRIPT), "--", str(test_file), "-q", "--timeout=30"] + args
    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    return result.returncode, metrics_dir


# ---------------------------------------------------------------------------
# Test 1 — capacity.json is produced under the metrics dir
# ---------------------------------------------------------------------------


def test_capacity_json_is_created(tmp_path: Path) -> None:
    """A run produces exactly one capacity.json under the metrics dir."""
    _rc, metrics_dir = _run_pytest_with_summary(tmp_path)

    capacity_files = list(metrics_dir.rglob("capacity.json"))
    assert capacity_files, (
        f"No capacity.json found under {metrics_dir}. "
        "pytest-with-summary.sh must write .cognitive-os/metrics/test-runs/<ts>/capacity.json "
        "on every invocation (ADR-068 Phase 2)."
    )
    assert len(capacity_files) == 1, (
        f"Expected exactly 1 capacity.json, found {len(capacity_files)}: {capacity_files}"
    )
    # File must be a valid JSON file (not empty, not truncated).
    content = capacity_files[0].read_text(encoding="utf-8")
    assert content.strip(), "capacity.json is empty"
    json.loads(content)  # raises if invalid


# ---------------------------------------------------------------------------
# Test 2 — capacity.json contains all required ADR-068 keys
# ---------------------------------------------------------------------------


def test_capacity_json_has_required_keys(tmp_path: Path) -> None:
    """The produced capacity.json contains every key mandated by ADR-068."""
    _rc, metrics_dir = _run_pytest_with_summary(tmp_path)

    capacity_file = next(metrics_dir.rglob("capacity.json"))
    payload = json.loads(capacity_file.read_text(encoding="utf-8"))

    missing = REQUIRED_KEYS - set(payload.keys())
    assert not missing, (
        f"capacity.json is missing ADR-068 required keys: {sorted(missing)}\n"
        f"Present keys: {sorted(payload.keys())}"
    )

    # Spot-check types for a few critical fields.
    assert isinstance(payload["timestamp_utc"], str) and payload["timestamp_utc"], (
        "timestamp_utc must be a non-empty string"
    )
    assert isinstance(payload["cores"], int) and payload["cores"] >= 1, (
        "cores must be a positive integer"
    )
    assert isinstance(payload["workers_chosen"], str), "workers_chosen must be a string"
    assert isinstance(payload["rule_fired"], str) and payload["rule_fired"], (
        "rule_fired must be a non-empty string"
    )


# ---------------------------------------------------------------------------
# Test 3 — COS_PYTEST_WORKERS=8 is reflected in workers_chosen and rule_fired
# ---------------------------------------------------------------------------


def test_env_override_reflected_in_capacity_json(tmp_path: Path) -> None:
    """When COS_PYTEST_WORKERS=8, workers_chosen='8' and rule_fired='env_override'."""
    _rc, metrics_dir = _run_pytest_with_summary(
        tmp_path,
        extra_env={"COS_PYTEST_WORKERS": "8"},
    )

    capacity_file = next(metrics_dir.rglob("capacity.json"))
    payload = json.loads(capacity_file.read_text(encoding="utf-8"))

    assert payload["workers_chosen"] == "8", (
        f"Expected workers_chosen='8', got '{payload['workers_chosen']}'. "
        "COS_PYTEST_WORKERS=8 must be reflected in capacity.json."
    )
    assert payload["rule_fired"] == "env_override", (
        f"Expected rule_fired='env_override', got '{payload['rule_fired']}'. "
        "An env override must set rule_fired to 'env_override'."
    )
    assert payload["pytest_args_inferred"] == "-n 8", (
        f"Expected pytest_args_inferred='-n 8', got '{payload['pytest_args_inferred']}'"
    )
