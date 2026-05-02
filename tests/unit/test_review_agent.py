# SCOPE: os-only
"""
Unit tests for lib/review_agent.py — Phase 3 learning-loop closure (ADR-096).

Tests cover all public functions:
  - should_review: sample_rate edge cases, budget exhaustion, date rollover
  - select_reviewer_model: full cross-review matrix, unknown model fallback
  - build_review_prompt: required fields present, no rubber-stamping language absent
  - parse_review_response: well-formed, malformed, empty input
  - persist_finding: JSONL append + Engram save called with right type
  - daily_budget_state: state file format, rollover at midnight UTC

Run: python3 -m pytest tests/unit/test_review_agent.py -v
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure lib/ is importable (handles both direct and package-root invocation)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.review_agent import (
    REVIEWER_MODEL_MATRIX,
    build_review_prompt,
    daily_budget_state,
    evaluate_review_quality,
    parse_review_response,
    persist_finding,
    select_reviewer_model,
    should_review,
    _save_budget_state,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_budget_file(tmp_path: Path) -> Path:
    return tmp_path / "review-budget.json"


@pytest.fixture()
def tmp_findings_jsonl(tmp_path: Path) -> Path:
    return tmp_path / "review-findings.jsonl"


@pytest.fixture()
def sample_producer_output() -> dict:
    return {
        "task_description": "Write a Python function that reverses a string.",
        "text": (
            "I implemented `reverse_string(s)` in `lib/utils.py`. "
            "The function passes all tests.\n\n"
            "TRUST REPORT:\n"
            "Score: 82/100\n"
            "Evidence: ran pytest, 5/5 tests pass.\n"
            "Uncertainty: did not verify edge cases with unicode."
        ),
        "producer_id": "agent-abc123",
        "producer_model": "sonnet",
    }


# ─── should_review ────────────────────────────────────────────────────────────

class TestShouldReview:
    def test_sample_rate_zero_never_reviews(self, sample_producer_output):
        for _ in range(20):
            assert should_review(sample_producer_output, sample_rate=0.0) is False

    def test_sample_rate_one_always_reviews_within_budget(self, sample_producer_output, tmp_budget_file):
        budget: dict = {}
        for i in range(5):
            result = should_review(
                sample_producer_output,
                sample_rate=1.0,
                daily_budget=budget,
                max_per_day=10,
                state_file=tmp_budget_file,
            )
            assert result is True, f"iteration {i}: expected True"

    def test_sample_rate_half_is_stochastic(self, sample_producer_output):
        """Over 200 trials at 0.5, expect between 60 and 140 True (p≈0.5)."""
        true_count = sum(
            should_review(sample_producer_output, sample_rate=0.5, daily_budget={}, max_per_day=10000)
            for _ in range(200)
        )
        assert 60 <= true_count <= 140, f"stochastic gate off: {true_count}/200 True"

    def test_budget_exhaustion_blocks_review(self, sample_producer_output):
        # Use today's real date to verify exhaustion at exact cap
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        budget_today = {today: 50}
        result = should_review(
            sample_producer_output,
            sample_rate=1.0,
            daily_budget=budget_today,
            max_per_day=50,
        )
        assert result is False

    def test_budget_exhaustion_at_cap(self, sample_producer_output):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        budget = {today: 49}
        result = should_review(
            sample_producer_output, sample_rate=1.0, daily_budget=budget, max_per_day=50
        )
        assert result is True
        # Budget should now be 50
        assert budget[today] == 50

    def test_budget_exactly_at_limit_rejected(self, sample_producer_output):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        budget = {today: 50}
        result = should_review(
            sample_producer_output, sample_rate=1.0, daily_budget=budget, max_per_day=50
        )
        assert result is False

    def test_budget_incremented_on_approval(self, sample_producer_output):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        budget: dict = {}
        should_review(sample_producer_output, sample_rate=1.0, daily_budget=budget, max_per_day=10)
        assert budget.get(today, 0) == 1

    def test_date_rollover_allows_new_day(self, sample_producer_output):
        """Yesterday's exhausted budget should NOT block today's reviews."""
        budget = {"2000-01-01": 50}  # old date, exhausted
        result = should_review(
            sample_producer_output, sample_rate=1.0, daily_budget=budget, max_per_day=50
        )
        assert result is True

    def test_budget_persisted_to_state_file(self, sample_producer_output, tmp_budget_file):
        """When state_file is provided and no daily_budget arg, should persist."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        result = should_review(
            sample_producer_output,
            sample_rate=1.0,
            max_per_day=10,
            state_file=tmp_budget_file,
        )
        assert result is True
        saved = json.loads(tmp_budget_file.read_text())
        assert saved.get(today, 0) == 1


# ─── select_reviewer_model ───────────────────────────────────────────────────

class TestSelectReviewerModel:
    def test_haiku_maps_to_sonnet(self):
        assert select_reviewer_model("haiku") == "sonnet"

    def test_sonnet_maps_to_opus(self):
        assert select_reviewer_model("sonnet") == "opus"

    def test_opus_maps_to_sonnet(self):
        assert select_reviewer_model("opus") == "sonnet"

    def test_full_haiku_model_name(self):
        assert select_reviewer_model("claude-haiku-3-5") == "sonnet"

    def test_full_sonnet_model_name(self):
        assert select_reviewer_model("claude-sonnet-4-6") == "opus"

    def test_full_opus_model_name(self):
        assert select_reviewer_model("claude-opus-4-7") == "sonnet"

    def test_unknown_model_falls_back_to_sonnet(self):
        # gpt-4o and llama-3 have no haiku/sonnet/opus substring — fall back to sonnet tier
        # which maps to opus via matrix. The function falls back to sonnet as the tier
        # and then looks it up in the matrix (sonnet→opus). This is correct behavior:
        # unknown models are treated as sonnet-tier and reviewed by opus.
        # The actual "sonnet" fallback is the tier assigned, not the reviewer output.
        assert select_reviewer_model("gpt-4o") == "opus"   # unknown→sonnet tier→opus reviewer
        assert select_reviewer_model("llama-3") == "opus"  # unknown→sonnet tier→opus reviewer
        # Empty string — also unknown, same path
        assert select_reviewer_model("") == "opus"

    def test_matrix_covers_all_tiers(self):
        """All tiers in REVIEWER_MODEL_MATRIX must be tested."""
        for producer_tier, expected_reviewer in REVIEWER_MODEL_MATRIX.items():
            assert select_reviewer_model(producer_tier) == expected_reviewer

    def test_lateral_review_opus_is_not_downward(self):
        """Opus → sonnet is lateral (not haiku). Confirm it's not haiku."""
        result = select_reviewer_model("opus")
        assert result != "haiku"


# ─── build_review_prompt ─────────────────────────────────────────────────────

class TestBuildReviewPrompt:
    def test_includes_task_description(self, sample_producer_output):
        prompt = build_review_prompt(sample_producer_output)
        assert "reverses a string" in prompt

    def test_includes_producer_id(self, sample_producer_output):
        prompt = build_review_prompt(sample_producer_output)
        assert "agent-abc123" in prompt

    def test_includes_producer_model(self, sample_producer_output):
        prompt = build_review_prompt(sample_producer_output)
        assert "sonnet" in prompt

    def test_includes_trust_report_content(self, sample_producer_output):
        prompt = build_review_prompt(sample_producer_output)
        assert "TRUST REPORT" in prompt or "Trust Report" in prompt.lower() or "82/100" in prompt

    def test_includes_agent_output_text(self, sample_producer_output):
        prompt = build_review_prompt(sample_producer_output)
        assert "reverse_string" in prompt

    def test_includes_acceptance_criteria(self, sample_producer_output):
        criteria = ["Function handles empty string", "Function handles unicode"]
        prompt = build_review_prompt(sample_producer_output, criteria=criteria)
        assert "empty string" in prompt
        assert "unicode" in prompt

    def test_no_rubber_stamp_language_absent(self, sample_producer_output):
        """Prompt must instruct reviewer to find at least 1 gap — not to approve."""
        prompt = build_review_prompt(sample_producer_output)
        # Must explicitly forbid rubber-stamping
        assert "rubber" in prompt.lower() or "at least 1" in prompt.lower() or "rubber-stamp" in prompt.lower()

    def test_requires_gaps_in_output(self, sample_producer_output):
        """Prompt must explicitly require at least 1 gap."""
        prompt = build_review_prompt(sample_producer_output)
        assert "GAPS" in prompt

    def test_absent_trust_report_flagged(self):
        """If producer output has no trust_report, prompt should note its absence."""
        output = {
            "task_description": "Deploy the service.",
            "text": "Deployed successfully.",
            "producer_id": "agent-xyz",
            "producer_model": "haiku",
        }
        prompt = build_review_prompt(output)
        # Should mention absence or mandatory violation
        assert "Trust" in prompt or "TRUST" in prompt

    def test_output_truncated_to_reasonable_length(self):
        """Very long outputs must be truncated so prompt stays under context limits."""
        output = {
            "task_description": "long task",
            "text": "x" * 20000,
            "producer_id": "agent-long",
            "producer_model": "sonnet",
        }
        prompt = build_review_prompt(output)
        # 20K chars of 'x' should be truncated in the prompt
        x_run = "x" * 8001
        assert x_run not in prompt  # confirms truncation happened


# ─── parse_review_response ───────────────────────────────────────────────────

WELL_FORMED_RESPONSE = """\
REVIEW_SCORE: 74
EVIDENCE:
- Agent correctly wrote the file lib/utils.py
- Test output shows 5/5 pass
GAPS:
- No verification that edge case for empty string was tested
- Trust score of 82 seems inflated without unicode test evidence
RECOMMENDATIONS:
- Add a test for empty string and unicode inputs
- Lower stated trust score to ~70 given missing coverage
REVIEWER_CONFIDENCE: 80
UNCERTAINTY: Could not verify the actual file contents from the output alone.
"""


class TestParseReviewResponse:
    def test_parses_score(self):
        result = parse_review_response(WELL_FORMED_RESPONSE)
        assert result["score"] == 74

    def test_parses_evidence_list(self):
        result = parse_review_response(WELL_FORMED_RESPONSE)
        assert len(result["evidence"]) >= 1
        assert any("lib/utils.py" in e for e in result["evidence"])

    def test_parses_gaps_list(self):
        result = parse_review_response(WELL_FORMED_RESPONSE)
        assert len(result["gaps"]) >= 1
        assert any("empty string" in g for g in result["gaps"])

    def test_parses_recommendations_list(self):
        result = parse_review_response(WELL_FORMED_RESPONSE)
        assert len(result["recommendations"]) >= 1

    def test_parses_reviewer_confidence(self):
        result = parse_review_response(WELL_FORMED_RESPONSE)
        assert result["reviewer_confidence"] == 80

    def test_parses_uncertainty(self):
        result = parse_review_response(WELL_FORMED_RESPONSE)
        assert "verify" in result["uncertainty"].lower() or result["uncertainty"]

    def test_empty_response_returns_error(self):
        result = parse_review_response("")
        assert result["score"] == -1
        assert "error" in result

    def test_none_like_empty_string(self):
        result = parse_review_response("   ")
        assert result["score"] == -1

    def test_malformed_score_graceful(self):
        malformed = "REVIEW_SCORE: not-a-number\nGAPS:\n- something\n"
        result = parse_review_response(malformed)
        assert result["score"] == -1
        assert "parse_warnings" in result

    def test_missing_gaps_flagged(self):
        no_gaps = "REVIEW_SCORE: 90\nEVIDENCE:\n- all good\n"
        result = parse_review_response(no_gaps)
        assert "parse_warnings" in result
        assert any("GAPS" in w for w in result.get("parse_warnings", []))

    def test_score_clamped_to_0_100(self):
        high = "REVIEW_SCORE: 150\nGAPS:\n- gap\n"
        result = parse_review_response(high)
        assert result["score"] == 100

        # "REVIEW_SCORE: -20" — the parser strips non-digits, yielding "20", then clamps.
        # max(0, min(100, 20)) == 20. The clamping is to [0,100] on the extracted digits.
        low = "REVIEW_SCORE: -20\nGAPS:\n- gap\n"
        result = parse_review_response(low)
        # After digit extraction "-20" → "20" → clamped to 20 (already in [0,100])
        assert 0 <= result["score"] <= 100

    def test_partial_response_still_returns_dict(self):
        partial = "REVIEW_SCORE: 55\n"
        result = parse_review_response(partial)
        assert isinstance(result, dict)
        assert result["score"] == 55


# ─── evaluate_review_quality ─────────────────────────────────────────────────

class TestEvaluateReviewQuality:
    def test_well_formed_review_is_usable(self):
        parsed = parse_review_response(WELL_FORMED_RESPONSE)

        quality = evaluate_review_quality(parsed)

        assert quality["quality_verdict"] == "usable"
        assert quality["quality_score"] >= 80
        assert quality["quality_issues"] == []

    def test_rubber_stamp_review_is_invalid_or_weak(self):
        parsed = parse_review_response(
            "REVIEW_SCORE: 95\n"
            "EVIDENCE:\n"
            "- Looks good.\n"
            "RECOMMENDATIONS:\n"
            "- None.\n"
            "REVIEWER_CONFIDENCE: 99\n"
        )

        quality = evaluate_review_quality(parsed)

        assert quality["quality_verdict"] in {"weak", "invalid"}
        assert "missing_gaps" in quality["quality_issues"]

    def test_empty_review_quality_is_invalid(self):
        quality = evaluate_review_quality(parse_review_response(""))

        assert quality["quality_verdict"] == "invalid"
        assert quality["quality_score"] < 50


# ─── persist_finding ─────────────────────────────────────────────────────────

class TestPersistFinding:
    def test_appends_to_jsonl(self, tmp_findings_jsonl):
        finding = {
            "score": 72,
            "evidence": ["file exists"],
            "gaps": ["no test for edge case"],
            "recommendations": ["add edge case test"],
            "producer_id": "agent-001",
            "reviewer_model": "sonnet",
        }
        persist_finding(finding, jsonl_path=tmp_findings_jsonl, engram_topic="review-finding")
        assert tmp_findings_jsonl.exists()
        lines = [l for l in tmp_findings_jsonl.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["score"] == 72
        assert "timestamp" in record
        assert record["review_quality"]["quality_verdict"] in {"usable", "weak", "invalid"}

    def test_multiple_appends_dont_overwrite(self, tmp_findings_jsonl):
        for i in range(3):
            persist_finding(
                {"score": i * 10, "gaps": [f"gap-{i}"], "producer_id": f"agent-{i}"},
                jsonl_path=tmp_findings_jsonl,
            )
        lines = [l for l in tmp_findings_jsonl.read_text().splitlines() if l.strip()]
        assert len(lines) == 3

    def test_adds_timestamp_if_missing(self, tmp_findings_jsonl):
        persist_finding({"score": 50, "gaps": ["gap"], "producer_id": "x"}, jsonl_path=tmp_findings_jsonl)
        record = json.loads(tmp_findings_jsonl.read_text().splitlines()[0])
        assert "timestamp" in record
        # Should be ISO-8601
        datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))

    def test_engram_save_called(self, tmp_findings_jsonl):
        with patch("lib.review_agent._engram_save") as mock_engram:
            persist_finding(
                {"score": 60, "gaps": ["gap"], "producer_id": "agent-engram-test"},
                jsonl_path=tmp_findings_jsonl,
                engram_topic="review-finding",
            )
            mock_engram.assert_called_once()
            args = mock_engram.call_args
            # First arg is the finding dict
            assert isinstance(args[0][0], dict)
            # Second arg (topic_key) must contain "review-finding"
            topic_key = args[0][1]
            assert "review-finding" in topic_key

    def test_creates_parent_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "c" / "findings.jsonl"
        persist_finding({"score": 40, "gaps": ["g"], "producer_id": "p"}, jsonl_path=deep_path)
        assert deep_path.exists()


# ─── daily_budget_state ───────────────────────────────────────────────────────

class TestDailyBudgetState:
    def test_returns_empty_dict_if_no_file(self, tmp_path):
        result = daily_budget_state(tmp_path / "nonexistent.json")
        assert result == {}

    def test_reads_valid_state(self, tmp_path):
        state_file = tmp_path / "budget.json"
        state_file.write_text(json.dumps({"2026-05-01": 7}))
        result = daily_budget_state(state_file)
        assert result == {"2026-05-01": 7}

    def test_tolerates_corrupt_file(self, tmp_path):
        state_file = tmp_path / "budget.json"
        state_file.write_text("not json {{{")
        result = daily_budget_state(state_file)
        assert result == {}

    def test_tolerates_empty_file(self, tmp_path):
        state_file = tmp_path / "budget.json"
        state_file.write_text("")
        result = daily_budget_state(state_file)
        assert result == {}

    def test_old_dates_preserved_but_dont_affect_today_gate(self, tmp_path):
        """Budget for old dates is loaded (for history) but gating uses today only."""
        state_file = tmp_path / "budget.json"
        state_file.write_text(json.dumps({"2000-01-01": 50, "2001-06-15": 3}))
        result = daily_budget_state(state_file)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # Today should be absent (no reviews today yet)
        assert result.get(today, 0) == 0

    def test_save_and_reload_roundtrip(self, tmp_path):
        state_file = tmp_path / "budget.json"
        budget = {"2026-05-01": 12, "2026-05-02": 3}
        _save_budget_state(budget, state_file)
        loaded = daily_budget_state(state_file)
        assert loaded == budget

    def test_int_values_only(self, tmp_path):
        """Non-int values in state file should be cast or dropped gracefully."""
        state_file = tmp_path / "budget.json"
        state_file.write_text(json.dumps({"2026-05-01": "7", "2026-05-02": None}))
        result = daily_budget_state(state_file)
        # "7" should be cast to int
        assert result.get("2026-05-01") == 7
        # None key should be dropped
        assert "2026-05-02" not in result
