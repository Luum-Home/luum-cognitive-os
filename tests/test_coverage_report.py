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


@pytest.fixture(scope="module")
def coverage_report_result(project_root):
    """Run the expensive coverage report once and share the output.

    The contract under test is the report surface, not repeated execution. Running
    the same repository-wide scan once per assertion made this module exceed the
    30s pytest timeout in broad serial lanes while adding no behavioral coverage.
    """
    script = project_root / "tests" / "coverage-report.sh"
    if not script.exists():
        pytest.skip("coverage-report.sh not found")

    return subprocess.run(
        ["bash", str(script)],
        capture_output=True,
        text=True,
        cwd=str(project_root),
        timeout=60,
    )


@pytest.mark.system
class TestCoverageReport:
    """Tests that the coverage report script produces valid output."""

    def test_coverage_report_runs(self, coverage_report_result):
        """Ensure the coverage report script exits 0 and produces output."""
        # Coverage report always exits 0 (it is a reporting tool)
        assert coverage_report_result.returncode == 0, (
            f"coverage report should exit 0: {coverage_report_result.stderr}"
        )

    def test_coverage_report_includes_dimensions(self, coverage_report_result):
        """The report should include all four coverage dimensions."""
        output = coverage_report_result.stdout

        for dimension in ["Infrastructure", "Skill", "State Transition", "Hook"]:
            assert dimension in output, (
                f"coverage report should include '{dimension}' dimension"
            )

    def test_coverage_report_includes_summary(self, coverage_report_result):
        output = coverage_report_result.stdout
        assert "Composite" in output or "Summary" in output, (
            "coverage report should include a summary section"
        )
