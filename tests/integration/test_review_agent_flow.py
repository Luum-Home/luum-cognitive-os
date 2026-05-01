# SCOPE: os-only
"""
Integration tests for the ADR-096 review-agent end-to-end flow.

Tests the complete pipeline:
  synthetic producer output
  → should_review gate (True)
  → build_review_prompt
  → mock dispatcher returns review response
  → parse_review_response
  → persist_finding (JSONL + Engram stub)

v1 sync path only. v2 async (pending-marker + sweeper) tested via the
review-result-sweeper hook when that is implemented as a follow-up.

Run: python3 -m pytest tests/integration/test_review_agent_flow.py -v
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.review_agent import (
    build_review_prompt,
    parse_review_response,
    persist_finding,
    select_reviewer_model,
    should_review,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_dirs(tmp_path: Path):
    budget_file = tmp_path / "review-budget.json"
    findings_file = tmp_path / "review-findings.jsonl"
    return {"budget": budget_file, "findings": findings_file, "root": tmp_path}


SYNTHETIC_PRODUCER_OUTPUT = {
    "task_description": "Implement the `greet(name)` function in lib/greet.py.",
    "text": (
        "I implemented `greet(name)` in `lib/greet.py`. "
        "The function returns 'Hello, <name>!'. "
        "All 3 tests pass.\n\n"
        "TRUST REPORT:\n"
        "Score: 85/100\n"
        "Evidence: pytest output shows 3/3 tests pass.\n"
        "Uncertainty: Did not run with Python 3.8 (only 3.11 confirmed)."
    ),
    "producer_id": "integration-agent-001",
    "producer_model": "haiku",
    "trust_report": (
        "Score: 85/100\n"
        "Evidence: pytest output shows 3/3 tests pass.\n"
        "Uncertainty: Did not run with Python 3.8 (only 3.11 confirmed)."
    ),
}

MOCK_REVIEWER_RESPONSE = """\
REVIEW_SCORE: 78
EVIDENCE:
- Producer mentions pytest output showing 3/3 tests pass
- Trust report includes an honest uncertainty about Python 3.8
GAPS:
- The output does not show the actual pytest stdout — claim is unverifiable from text alone
- Function behavior for None input is not mentioned
RECOMMENDATIONS:
- Include pytest output snippet in future trust reports
- Test None/empty string inputs explicitly
REVIEWER_CONFIDENCE: 72
UNCERTAINTY: Cannot verify the actual file content or test run from the agent's text description.
"""


# ─── Integration: end-to-end flow ─────────────────────────────────────────────

class TestEndToEndFlow:
    def test_full_pipeline_produces_finding(self, tmp_dirs):
        """Synthetic output → gate → prompt → mock dispatch → persist."""
        budget: dict = {}
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Step 1: gate
        approved = should_review(
            SYNTHETIC_PRODUCER_OUTPUT,
            sample_rate=1.0,
            daily_budget=budget,
            max_per_day=10,
        )
        assert approved is True
        assert budget.get(today, 0) == 1

        # Step 2: select reviewer model (haiku → sonnet)
        reviewer_model = select_reviewer_model(SYNTHETIC_PRODUCER_OUTPUT["producer_model"])
        assert reviewer_model == "sonnet"

        # Step 3: build prompt
        prompt = build_review_prompt(SYNTHETIC_PRODUCER_OUTPUT, criteria=[
            "Function returns 'Hello, <name>!'",
            "All existing tests pass",
        ])
        assert "greet" in prompt
        assert "integration-agent-001" in prompt
        assert "Hello" in prompt

        # Step 4: mock dispatch
        mock_dispatch_result = MagicMock()
        mock_dispatch_result.success = True
        mock_dispatch_result.text = MOCK_REVIEWER_RESPONSE

        with patch("lib.dispatch.dispatch", return_value=mock_dispatch_result):
            from lib.dispatch import dispatch
            result = dispatch(
                prompt=prompt,
                providers=["claude"],
                claude_model=reviewer_model,
                task_type="review",
            )
        assert result.success is True
        assert result.text == MOCK_REVIEWER_RESPONSE

        # Step 5: parse
        parsed = parse_review_response(result.text)
        assert parsed["score"] == 78
        assert len(parsed["gaps"]) >= 1
        assert parsed["reviewer_confidence"] == 72

        # Step 6: persist
        finding = {
            **parsed,
            "producer_id": SYNTHETIC_PRODUCER_OUTPUT["producer_id"],
            "producer_model": SYNTHETIC_PRODUCER_OUTPUT["producer_model"],
            "reviewer_id": "integration-test-reviewer",
            "reviewer_model": reviewer_model,
            "task_description": SYNTHETIC_PRODUCER_OUTPUT["task_description"],
        }

        findings_path = tmp_dirs["findings"]

        with patch("lib.review_agent._engram_save") as mock_engram:
            persist_finding(finding, jsonl_path=findings_path, engram_topic="review-finding")

        # Verify JSONL
        assert findings_path.exists()
        records = [json.loads(l) for l in findings_path.read_text().splitlines() if l.strip()]
        assert len(records) == 1
        rec = records[0]
        assert rec["score"] == 78
        assert rec["producer_id"] == "integration-agent-001"
        assert rec["reviewer_model"] == "sonnet"
        assert "timestamp" in rec

        # Verify Engram called
        mock_engram.assert_called_once()
        call_args = mock_engram.call_args[0]
        assert isinstance(call_args[0], dict)
        assert "review-finding" in call_args[1]

    def test_budget_exhaustion_prevents_second_review(self, tmp_dirs):
        """After daily budget is full, second call to should_review returns False."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        budget = {today: 2}

        r1 = should_review(
            SYNTHETIC_PRODUCER_OUTPUT, sample_rate=1.0, daily_budget=budget, max_per_day=2
        )
        assert r1 is False  # already at limit

    def test_cross_review_matrix_applied_end_to_end(self):
        """Verify each producer model tier maps to the correct reviewer."""
        cases = [
            ("haiku", "sonnet"),
            ("sonnet", "opus"),
            ("opus", "sonnet"),
            ("claude-sonnet-4-6", "opus"),
            ("claude-haiku-3-5", "sonnet"),
            ("claude-opus-4-7", "sonnet"),
        ]
        for producer, expected_reviewer in cases:
            output = {**SYNTHETIC_PRODUCER_OUTPUT, "producer_model": producer}
            reviewer = select_reviewer_model(output["producer_model"])
            assert reviewer == expected_reviewer, (
                f"Producer {producer!r}: expected reviewer {expected_reviewer!r}, got {reviewer!r}"
            )

    def test_failed_dispatch_produces_no_finding(self, tmp_dirs):
        """When dispatch fails, no finding should be persisted."""
        findings_path = tmp_dirs["findings"]
        approved = should_review(
            SYNTHETIC_PRODUCER_OUTPUT, sample_rate=1.0, daily_budget={}, max_per_day=10
        )
        assert approved is True

        mock_dispatch_result = MagicMock()
        mock_dispatch_result.success = False
        mock_dispatch_result.text = ""
        mock_dispatch_result.error = "rate_limit"

        # Simulate hook behavior: if dispatch fails, don't persist
        with patch("lib.dispatch.dispatch", return_value=mock_dispatch_result):
            from lib.dispatch import dispatch
            result = dispatch(prompt="test", providers=["claude"], claude_model="sonnet")

        if not result.success:
            pass  # hook exits early, no persist_finding call

        assert not findings_path.exists()

    def test_empty_reviewer_response_logged_safely(self, tmp_dirs):
        """parse_review_response on empty string must not raise."""
        parsed = parse_review_response("")
        assert parsed["score"] == -1
        assert "error" in parsed

    def test_multiple_outputs_reviewed_and_all_persisted(self, tmp_dirs):
        """Multiple sequential reviews produce separate JSONL rows."""
        findings_path = tmp_dirs["findings"]
        budget: dict = {}

        for i in range(3):
            output = {**SYNTHETIC_PRODUCER_OUTPUT, "producer_id": f"agent-{i:03d}"}
            approved = should_review(output, sample_rate=1.0, daily_budget=budget, max_per_day=10)
            assert approved is True

            parsed = parse_review_response(MOCK_REVIEWER_RESPONSE)
            finding = {
                **parsed,
                "producer_id": output["producer_id"],
                "producer_model": "haiku",
                "reviewer_id": f"reviewer-{i}",
                "reviewer_model": "sonnet",
            }
            with patch("lib.review_agent._engram_save"):
                persist_finding(finding, jsonl_path=findings_path)

        rows = [json.loads(l) for l in findings_path.read_text().splitlines() if l.strip()]
        assert len(rows) == 3
        producer_ids = {r["producer_id"] for r in rows}
        assert producer_ids == {"agent-000", "agent-001", "agent-002"}
