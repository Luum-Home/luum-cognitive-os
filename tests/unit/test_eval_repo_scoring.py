"""Unit tests for tests/utils/eval_repo_score.py

Validates repository evaluation scoring functions: license scoring (MIT, Apache,
BSD, GPL, AGPL, unknown), activity scoring by days since last commit,
auto-rejection logic (AGPL, inactive, archived, passing repos), score
classification (ADOPT/TRIAL/ASSESS/HOLD/REJECT), and weighted score calculation.
"""
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# Ensure tests/utils is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from utils.eval_repo_score import (
    score_license,
    score_activity,
    should_auto_reject,
    classify_score,
    calculate_weighted_score,
)


class TestScoreLicense:
    """score_license assigns correct scores by license type."""

    @pytest.mark.parametrize("license_id,expected_score", [
        ("MIT", 10),
        ("Apache-2.0", 10),
        ("BSD-3-Clause", 8),
        ("GPL-3.0", 5),
        ("AGPL-3.0", 0),
        ("", 2),
    ])
    def test_license_scores(self, license_id, expected_score):
        result = score_license(license_id)
        assert result == expected_score


class TestScoreActivity:
    """score_activity assigns scores based on days since last commit."""

    @pytest.mark.parametrize("days,expected_score", [
        (15, 10),    # <= 30 days
        (60, 8),     # <= 90 days
        (120, 6),    # <= 180 days
        (300, 3),    # <= 365 days
        (400, 0),    # > 365 days
    ])
    def test_activity_scores(self, days, expected_score):
        result = score_activity(days)
        assert result == expected_score


class TestShouldAutoReject:
    """should_auto_reject applies auto-rejection rules for repos."""

    def test_reject_agpl_license(self):
        result = should_auto_reject("AGPL-3.0", 30, False)
        assert result == "REJECT:license:AGPL-3.0"

    def test_hold_inactive(self):
        result = should_auto_reject("MIT", 400, False)
        assert result == "HOLD:inactive:400d"

    def test_reject_archived(self):
        result = should_auto_reject("MIT", 30, True)
        assert result == "REJECT:archived"

    def test_pass_good_repo(self):
        result = should_auto_reject("MIT", 30, False)
        assert result == "PASS"


class TestClassifyScore:
    """classify_score maps numeric scores to category labels."""

    @pytest.mark.parametrize("score,expected_class", [
        ("8.5", "ADOPT"),
        ("8.0", "ADOPT"),
        ("7.0", "TRIAL"),
        ("6.0", "TRIAL"),
        ("5.0", "ASSESS"),
        ("3.0", "HOLD"),
        ("1.0", "REJECT"),
    ])
    def test_classification(self, score, expected_class):
        result = classify_score(score)
        assert result == expected_class


class TestCalculateWeightedScore:
    """calculate_weighted_score computes correct weighted averages."""

    def test_perfect_score(self):
        result = calculate_weighted_score(10, 10, 10, 10, 10)
        assert result == "10.0"

    def test_zero_score(self):
        result = calculate_weighted_score(0, 0, 0, 0, 0)
        assert result == "0.0"
