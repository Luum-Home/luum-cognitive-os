from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-test-laptop-friendly"


def test_laptop_friendly_runner_help_documents_resource_caps() -> None:
    result = subprocess.run([str(SCRIPT), "--help"], text=True, capture_output=True, check=False)

    assert result.returncode == 0
    assert "COS_TEST_WORKERS_MAX=1" in result.stderr
    assert "COS_PYTEST_NICE_LEVEL=15" in result.stderr


def test_laptop_friendly_runner_rejects_zero_workers_before_execution() -> None:
    result = subprocess.run([str(SCRIPT), "--max-workers", "0", "--no-capsule", "true"], text=True, capture_output=True, check=False)

    assert result.returncode == 2
    assert "--max-workers must be >= 1" in result.stderr
