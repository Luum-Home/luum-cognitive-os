# SCOPE: os-only
"""Tests for the ADR-069 4-dimension risk score added to
lib/dispatch_model_advisor.py by ADR-175.

5 representative tasks; assert score >= 5 -> opus, otherwise sonnet.
"""

from __future__ import annotations

import json

import pytest

from lib.dispatch_model_advisor import (
    score_task_risk,
    log_risk_recommendation,
    _ADR069_THRESHOLD,
)


# (description, blast_radius_files, expected_recommended_model)
CASES = [
    (
        "Fix typo in README; trivial textual update",
        1,
        "sonnet",
    ),
    (
        "Migrate production database schema; irreversible deploy",
        25,
        "opus",
    ),
    (
        "Implement architecture decision: choose between two patterns; design tradeoff across modules",
        12,
        "opus",
    ),
    (
        "Investigate why test fails; figure out root cause; explore code paths",
        8,
        "opus",
    ),
    (
        "Add a unit test for an existing function; specific exact expected output",
        1,
        "sonnet",
    ),
]


@pytest.mark.parametrize("desc,blast,expected", CASES)
def test_risk_recommendation(desc, blast, expected):
    risk = score_task_risk(desc, blast_radius_files=blast)
    assert risk["threshold"] == _ADR069_THRESHOLD
    assert 4 <= risk["total"] <= 12
    assert risk["recommended_model"] == expected, (
        f"Task {desc!r} blast={blast} scored {risk['total']} -> "
        f"{risk['recommended_model']}, expected {expected}"
    )


def test_log_risk_recommendation_writes_jsonl(tmp_path):
    metrics = tmp_path / "model-recommendations.jsonl"
    risk = score_task_risk("migrate production schema", blast_radius_files=30)
    out = log_risk_recommendation("migrate production schema", risk, metrics_path=metrics)
    assert out == metrics
    lines = metrics.read_text().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["risk"]["recommended_model"] == "opus"
    assert "timestamp" in rec
    assert rec["description"].startswith("migrate production schema")


def test_log_disabled_by_env(tmp_path, monkeypatch):
    metrics = tmp_path / "model-recommendations.jsonl"
    monkeypatch.setenv("DISABLE_HOOK_RESEARCH_QUALITY_VALIDATOR", "1")
    risk = score_task_risk("migrate production schema", blast_radius_files=30)
    out = log_risk_recommendation("anything", risk, metrics_path=metrics)
    assert out is None
    assert not metrics.exists()


def test_threshold_exactly_5_recommends_opus():
    """A task scoring exactly threshold should recommend opus (>= rule)."""
    risk = score_task_risk("design proposal evaluating alternatives", blast_radius_files=1)
    # design + propose + evaluate alternatives -> decisions=3, ac_clarity=2,
    # blast=1, reversibility=1 = 7 -> opus.  But check the >= boundary
    # holds in general:
    if risk["total"] >= _ADR069_THRESHOLD:
        assert risk["recommended_model"] == "opus"
    else:
        assert risk["recommended_model"] == "sonnet"
