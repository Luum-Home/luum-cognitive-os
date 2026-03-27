"""Coverage report test -- verifies the coverage report script runs and
produces output for all four coverage dimensions.

Migrated from tests/coverage-report.sh.
"""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def project_root():
    return Path(__file__).resolve().parent.parent


@pytest.mark.system
class TestCoverageReport:
    """Tests that the coverage report script produces valid output."""

    def test_coverage_report_runs(self, project_root):
        """Ensure the coverage report script exits 0 and produces output."""
        script = project_root / "tests" / "coverage-report.sh"
        if not script.exists():
            pytest.skip("coverage-report.sh not found")

        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=60,
        )
        # Coverage report always exits 0 (it is a reporting tool)
        assert result.returncode == 0, f"coverage report should exit 0: {result.stderr}"

    def test_coverage_report_includes_dimensions(self, project_root):
        """The report should include all four coverage dimensions."""
        script = project_root / "tests" / "coverage-report.sh"
        if not script.exists():
            pytest.skip("coverage-report.sh not found")

        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=60,
        )
        output = result.stdout

        for dimension in ["Infrastructure", "Skill", "State Transition", "Hook"]:
            assert dimension in output, (
                f"coverage report should include '{dimension}' dimension"
            )

    def test_coverage_report_includes_summary(self, project_root):
        script = project_root / "tests" / "coverage-report.sh"
        if not script.exists():
            pytest.skip("coverage-report.sh not found")

        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=60,
        )
        assert "Composite" in result.stdout or "Summary" in result.stdout, (
            "coverage report should include a summary section"
        )
