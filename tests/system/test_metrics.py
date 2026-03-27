"""System tests for metrics infrastructure.

Verifies metrics directory existence and JSONL file validity.
Migrated from tests/infra/test-metrics.sh.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def project_root():
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def metrics_dir(project_root):
    path = project_root / ".cognitive-os" / "metrics"
    if not path.is_dir():
        pytest.fail(f"Metrics directory missing: {path}")
    return path


@pytest.mark.system
class TestMetricsInfrastructure:
    """Tests for the metrics directory and JSONL file validity."""

    def test_metrics_directory_exists(self, metrics_dir):
        assert metrics_dir.is_dir(), "metrics directory should exist"

    def test_jsonl_files_valid(self, metrics_dir):
        """Validate all JSONL files contain valid JSON per line."""
        jsonl_files = list(metrics_dir.glob("*.jsonl"))
        if not jsonl_files:
            pytest.skip("No JSONL files found in metrics directory")

        invalid_files = []
        for jsonl in jsonl_files:
            lines = jsonl.read_text().strip().split("\n")
            if not lines or (len(lines) == 1 and lines[0] == ""):
                continue  # Empty file is acceptable

            bad_lines = 0
            for i, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    bad_lines += 1

            if bad_lines > 0:
                invalid_files.append(f"{jsonl.name}: {bad_lines}/{len(lines)} invalid lines")

        assert not invalid_files, (
            f"Invalid JSONL files found: {'; '.join(invalid_files)}"
        )

    def test_metrics_file_sizes_reported(self, metrics_dir):
        """Report line counts and sizes for all metrics files (informational)."""
        jsonl_files = list(metrics_dir.glob("*.jsonl"))
        if not jsonl_files:
            pytest.skip("No JSONL files found")

        for jsonl in jsonl_files:
            text = jsonl.read_text()
            lines = len(text.strip().split("\n")) if text.strip() else 0
            size = jsonl.stat().st_size
            # This is informational -- always passes
            assert True, f"{jsonl.name}: {lines} lines, {size} bytes"
