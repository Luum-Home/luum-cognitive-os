"""Tests for lib/agent_output_extractor.py"""

import json
import os
import textwrap
import tempfile
import pytest

from lib.agent_output_extractor import (
    extract_assistant_text,
    extract_last_response,
    extract_tool_results,
    summarize_agent_output,
)

# Path to the shared fixture
FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "agent-output-sample.jsonl"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_jsonl(tmp_path, lines: list[dict]) -> str:
    """Write a list of dicts as JSONL to a temp file and return the path."""
    p = tmp_path / "output.jsonl"
    with open(p, "w") as fh:
        for obj in lines:
            fh.write(json.dumps(obj) + "\n")
    return str(p)


# ---------------------------------------------------------------------------
# extract_assistant_text
# ---------------------------------------------------------------------------

class TestExtractAssistantText:
    def test_returns_text_from_fixture(self):
        text = extract_assistant_text(FIXTURE_PATH)
        assert "I'll fix the bug in main.py by reading the file first." in text
        assert "I can see the function. Now I'll fix the bug." in text
        assert "The bug has been fixed." in text

    def test_no_tool_use_content_in_result(self):
        text = extract_assistant_text(FIXTURE_PATH)
        # Tool use entries should not appear in text output
        assert "tool_use" not in text
        assert "tool_001" not in text

    def test_messages_in_order_most_recent_last(self):
        text = extract_assistant_text(FIXTURE_PATH)
        idx_first = text.index("I'll fix the bug")
        idx_last = text.index("The bug has been fixed.")
        assert idx_first < idx_last

    def test_missing_file_returns_empty_string(self):
        result = extract_assistant_text("/nonexistent/path/agent.output")
        assert result == ""

    def test_empty_string_path_returns_empty(self):
        result = extract_assistant_text("")
        assert result == ""

    def test_malformed_lines_are_skipped(self, tmp_path):
        path = _write_jsonl(tmp_path, [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello"}], "usage": {}}},
        ])
        # Inject a malformed line in the middle
        with open(path, "a") as fh:
            fh.write("this is not json\n")
        with open(path, "a") as fh:
            fh.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "World"}], "usage": {}}}) + "\n")

        result = extract_assistant_text(path)
        assert "Hello" in result
        assert "World" in result

    def test_handles_compaction_boundary(self, tmp_path):
        lines = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Before compaction"}], "usage": {}}},
            {"type": "system", "subtype": "compact_boundary", "content": "Conversation compacted"},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "After compaction"}], "usage": {}}},
        ]
        path = _write_jsonl(tmp_path, lines)
        result = extract_assistant_text(path)
        assert "Before compaction" in result
        assert "After compaction" in result
        assert "compaction boundary" in result  # separator injected

    def test_non_assistant_types_excluded(self, tmp_path):
        lines = [
            {"type": "user", "message": {"content": "user message text"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "assistant response"}], "usage": {}}},
            {"type": "system", "content": "system message"},
        ]
        path = _write_jsonl(tmp_path, lines)
        result = extract_assistant_text(path)
        assert "assistant response" in result
        assert "user message text" not in result
        assert "system message" not in result

    def test_empty_file_returns_empty_string(self, tmp_path):
        p = tmp_path / "empty.jsonl"
        p.write_text("")
        assert extract_assistant_text(str(p)) == ""

    def test_no_text_blocks_returns_empty_string(self, tmp_path):
        lines = [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Read", "input": {}}], "usage": {}}},
        ]
        path = _write_jsonl(tmp_path, lines)
        assert extract_assistant_text(path) == ""


# ---------------------------------------------------------------------------
# extract_last_response
# ---------------------------------------------------------------------------

class TestExtractLastResponse:
    def test_returns_only_final_message(self):
        result = extract_last_response(FIXTURE_PATH)
        assert "The bug has been fixed." in result
        # Earlier messages should NOT appear
        assert "I'll fix the bug in main.py by reading the file first." not in result

    def test_missing_file_returns_empty(self):
        assert extract_last_response("/does/not/exist.output") == ""

    def test_single_message(self, tmp_path):
        lines = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Only message"}], "usage": {}}},
        ]
        path = _write_jsonl(tmp_path, lines)
        assert extract_last_response(path) == "Only message"

    def test_last_message_with_multiple_text_blocks(self, tmp_path):
        lines = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "First msg"}], "usage": {}}},
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": "Part A"},
                {"type": "tool_use", "id": "t1", "name": "Read", "input": {}},
                {"type": "text", "text": "Part B"},
            ], "usage": {}}},
        ]
        path = _write_jsonl(tmp_path, lines)
        result = extract_last_response(path)
        assert "Part A" in result
        assert "Part B" in result
        assert "First msg" not in result

    def test_tool_only_messages_skipped(self, tmp_path):
        lines = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Real answer"}], "usage": {}}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}], "usage": {}}},
        ]
        path = _write_jsonl(tmp_path, lines)
        result = extract_last_response(path)
        assert result == "Real answer"


# ---------------------------------------------------------------------------
# extract_tool_results
# ---------------------------------------------------------------------------

class TestExtractToolResults:
    def test_returns_list_of_dicts(self):
        results = extract_tool_results(FIXTURE_PATH)
        assert isinstance(results, list)
        assert len(results) >= 2

    def test_tool_names_resolved(self):
        results = extract_tool_results(FIXTURE_PATH)
        names = {r["tool_name"] for r in results}
        assert "Read" in names
        assert "Edit" in names

    def test_success_flag(self):
        results = extract_tool_results(FIXTURE_PATH)
        for r in results:
            assert r["success"] is True  # fixture has no errors

    def test_error_flag(self, tmp_path):
        lines = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}
            ], "usage": {}}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "permission denied", "is_error": True}
            ]}},
        ]
        path = _write_jsonl(tmp_path, lines)
        results = extract_tool_results(path)
        assert len(results) == 1
        assert results[0]["success"] is False
        assert results[0]["tool_name"] == "Bash"

    def test_missing_file_returns_empty_list(self):
        assert extract_tool_results("/no/such/file.output") == []

    def test_summary_truncated_at_300(self, tmp_path):
        long_content = "x" * 500
        lines = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Read", "input": {}}
            ], "usage": {}}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": long_content, "is_error": False}
            ]}},
        ]
        path = _write_jsonl(tmp_path, lines)
        results = extract_tool_results(path)
        assert results[0]["summary"].endswith("...")
        assert len(results[0]["summary"]) <= 303  # 300 + "..."


# ---------------------------------------------------------------------------
# summarize_agent_output
# ---------------------------------------------------------------------------

class TestSummarizeAgentOutput:
    def test_returns_dict_with_expected_keys(self):
        summary = summarize_agent_output(FIXTURE_PATH)
        assert isinstance(summary, dict)
        assert set(summary.keys()) == {"text", "tool_calls", "duration_ms", "tokens"}

    def test_text_contains_all_responses(self):
        summary = summarize_agent_output(FIXTURE_PATH)
        assert "I'll fix the bug" in summary["text"]
        assert "The bug has been fixed." in summary["text"]

    def test_tool_call_count(self):
        summary = summarize_agent_output(FIXTURE_PATH)
        # Fixture has Read + Edit = 2 tool calls
        assert summary["tool_calls"] == 2

    def test_duration_ms_positive(self):
        summary = summarize_agent_output(FIXTURE_PATH)
        assert summary["duration_ms"] > 0

    def test_tokens_positive(self):
        summary = summarize_agent_output(FIXTURE_PATH)
        assert summary["tokens"] > 0

    def test_missing_file_returns_zero_summary(self):
        summary = summarize_agent_output("/not/a/real/file.output")
        assert summary == {"text": "", "tool_calls": 0, "duration_ms": 0, "tokens": 0}

    def test_no_timestamps_duration_zero(self, tmp_path):
        lines = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "hello"}], "usage": {"output_tokens": 5}}},
        ]
        path = _write_jsonl(tmp_path, lines)
        summary = summarize_agent_output(path)
        assert summary["duration_ms"] == 0
        assert summary["tokens"] == 5
