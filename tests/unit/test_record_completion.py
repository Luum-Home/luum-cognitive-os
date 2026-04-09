"""Unit tests for lib/record_completion.py extraction helpers."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from lib.record_completion import (
    extract_skill_name,
    extract_trust_score,
    estimate_tokens,
    classify_task_type,
    detect_success,
    append_cost_event,
)


def make_payload(description="", prompt="", result=""):
    return {
        "tool_call_id": "toolu_abc123",
        "tool_name": "Agent",
        "tool_input": {"description": description, "prompt": prompt},
        "tool_response": {"result": result},
    }


class TestExtractSkillName:
    def test_prefers_description(self):
        data = make_payload(description="Implement auth endpoint", prompt="Other")
        assert extract_skill_name(data) == "Implement auth endpoint"

    def test_falls_back_to_prompt(self):
        data = make_payload(description="", prompt="Fix test\nmore detail")
        assert extract_skill_name(data) == "Fix test"

    def test_truncates_to_100(self):
        data = make_payload(description="A" * 150)
        assert len(extract_skill_name(data)) == 100

    def test_unknown_when_empty(self):
        data = make_payload(description="", prompt="")
        assert extract_skill_name(data) == "unknown"

    def test_strips_whitespace(self):
        data = make_payload(description="  Review PR  ")
        assert extract_skill_name(data) == "Review PR"

    def test_missing_tool_input(self):
        assert extract_skill_name({"tool_call_id": "x"}) == "unknown"


class TestExtractTrustScore:
    def test_machine_format(self):
        assert extract_trust_score("TRUST_REPORT: SCORE=85 STATUS=HIGH") == 85

    def test_human_format(self):
        assert extract_trust_score("Score: 92/100") == 92

    def test_legacy_format(self):
        assert extract_trust_score("done SCORE=67 ok") == 67

    def test_default_is_50(self):
        assert extract_trust_score("No trust report") == 50

    def test_clamps_above_100(self):
        assert extract_trust_score("SCORE=150") == 100

    def test_zero(self):
        assert extract_trust_score("TRUST_REPORT: SCORE=0") == 0


class TestEstimateTokens:
    def test_empty(self):
        assert estimate_tokens("") == 0

    def test_ratio(self):
        assert estimate_tokens("x" * 400) == 100


class TestClassifyTaskType:
    def test_implement(self):
        assert classify_task_type("Implement endpoint") == "implementation"

    def test_review(self):
        assert classify_task_type("Review PR") == "review"

    def test_fix(self):
        assert classify_task_type("Fix broken test") == "debugging"

    def test_doc(self):
        assert classify_task_type("Document API") == "documentation"

    def test_archive(self):
        assert classify_task_type("Archive change") == "archiving"

    def test_general(self):
        assert classify_task_type("Something vague") == "general"


class TestDetectSuccess:
    def test_success(self):
        assert detect_success("42 tests passed", make_payload()) is True

    def test_fail_keyword(self):
        assert detect_success("FAIL: 3 tests", make_payload()) is False

    def test_error_keyword(self):
        assert detect_success("ERROR: build", make_payload()) is False

    def test_is_error_flag(self):
        data = {"tool_call_id": "x", "tool_input": {},
                "tool_response": {"result": "out", "is_error": True}}
        assert detect_success("out", data) is False


class TestAppendCostEvent:
    def test_creates_file(self, tmp_path):
        append_cost_event(str(tmp_path), "task", 400)
        assert (tmp_path / "cost-events.jsonl").exists()

    def test_fields(self, tmp_path):
        append_cost_event(str(tmp_path), "Review PR", 200)
        event = json.loads((tmp_path / "cost-events.jsonl").read_text().strip())
        assert event["model"] == "sonnet"
        assert event["tokens_estimated"] == 200
        assert "timestamp" in event

    def test_pricing(self, tmp_path):
        append_cost_event(str(tmp_path), "task", 1000)
        event = json.loads((tmp_path / "cost-events.jsonl").read_text().strip())
        assert abs(event["estimated_cost_usd"] - 0.015) < 0.0001

    def test_survives_bad_dir(self):
        append_cost_event("/nonexistent/path", "task", 100)
