"""Integration tests for lib/ecosystem_evaluator.py — runs against the real repo.

Coverage:
1. test_live_check_plugins   — runs against real .claude/plugins/
2. test_live_check_tools     — runs against real ecosystem-tools.md
3. test_live_format_report   — produces a readable report from real data
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.ecosystem_evaluator import EcosystemEvaluator  # noqa: E402

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def evaluator() -> EcosystemEvaluator:
    return EcosystemEvaluator(str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# 1. Live plugin check
# ---------------------------------------------------------------------------

def test_live_check_plugins(evaluator: EcosystemEvaluator) -> None:
    result = evaluator.check_plugin_updates()
    # Result is always a list — may be empty if plugins dir is missing
    assert isinstance(result, list)
    for item in result:
        assert "plugin" in item
        assert "new_commits" in item
        assert "highlights" in item
        assert isinstance(item["highlights"], list)
        assert "adoption_candidates" in item


# ---------------------------------------------------------------------------
# 2. Live tool status check
# ---------------------------------------------------------------------------

def test_live_check_tools(evaluator: EcosystemEvaluator) -> None:
    result = evaluator.check_evaluated_tools()
    # File may not exist — always returns a list
    assert isinstance(result, list)
    for item in result:
        assert "name" in item
        assert item["status"] in ("EVALUATE", "WATCH")
        assert "is_stale" in item
        assert isinstance(item["is_stale"], bool)
        assert "days_since_eval" in item
        assert "recommendation" in item


# ---------------------------------------------------------------------------
# 3. Live format report
# ---------------------------------------------------------------------------

def test_live_format_report(evaluator: EcosystemEvaluator) -> None:
    report = evaluator.generate_evaluation_report()
    text = evaluator.format_report(report)

    assert isinstance(text, str)
    assert len(text) > 0
    # Must contain section headers
    assert "PLUGINS:" in text
    assert "EVALUATED TOOLS:" in text
    assert "REINVENTION RISK:" in text
    assert "===" in text
