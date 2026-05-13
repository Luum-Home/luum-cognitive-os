"""Integration tests for ComponentUsageTracker against the real repo.

These tests run against the actual luum-agent-os repository and validate
that the tracker produces sensible results without crashing.

Run with: pytest tests/integration/test_component_usage_live.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.component_usage_tracker import ComponentUsageTracker

# Project root is two levels up from this file (tests/integration/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def tracker() -> ComponentUsageTracker:
    return ComponentUsageTracker(str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Live scan tests
# ---------------------------------------------------------------------------


def test_live_scan_hooks(tracker: ComponentUsageTracker) -> None:
    result = tracker.scan_hook_registrations()

    assert isinstance(result["files_exist"], list)
    assert isinstance(result["registered"], list)
    assert isinstance(result["exists_but_unregistered"], list)
    assert isinstance(result["registered_but_missing"], list)
    assert 0.0 <= result["coverage_pct"] <= 100.0

    # The real repo has hook files
    assert len(result["files_exist"]) > 0, "Expected hook .sh files to exist"


def test_live_scan_libs(tracker: ComponentUsageTracker) -> None:
    result = tracker.scan_lib_imports()

    assert isinstance(result["imported"], list)
    assert isinstance(result["never_imported"], list)
    assert result["total_libs"] > 0, "Expected lib/*.py files to exist"
    assert 0.0 <= result["usage_pct"] <= 100.0

    # At least some libs should be imported (e.g. queue_drainer, skill_router)
    assert len(result["imported"]) > 0, "Expected some libs to be imported"


def test_live_generate_report(tracker: ComponentUsageTracker) -> None:
    report = tracker.generate_usage_report()

    assert "hooks" in report
    assert "libs" in report
    assert "rules" in report
    assert "skills" in report
    assert "dead_weight" in report

    dw = report["dead_weight"]
    assert dw["total_components"] > 100, "Expected 100+ total components in real repo"
    assert 0.0 <= dw["health_pct"] <= 100.0


def test_live_format_report(tracker: ComponentUsageTracker) -> None:
    report = tracker.generate_usage_report()
    text = tracker.format_usage_report(report)

    assert "COMPONENT USAGE REPORT" in text
    assert "HOOKS:" in text
    assert "LIBS:" in text
    assert "RULES:" in text
    assert "SKILLS:" in text
    assert "DEAD WEIGHT SUMMARY:" in text
    assert "Health score:" in text

    # Should contain actual numbers
    assert "%" in text
    # Should not be trivially short
    assert len(text) > 200
