# SCOPE: both
"""Unit tests for session parser."""
import json

import pytest
from lib.session_parser import (
    parse_session,
    list_sessions,
    get_session_metrics,
    discover_subagents,
    format_session_report,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session(tmp_path):
    """Create a mock Claude Code session JSONL file."""
    session_dir = tmp_path / ".claude" / "projects" / "test-project"
    session_dir.mkdir(parents=True)
    session_file = session_dir / "abc123.jsonl"

    lines = [
        # Queue operation (should be skipped)
        json.dumps({
            "type": "queue-operation",
            "operation": "enqueue",
            "timestamp": "2026-03-28T10:00:00Z",
            "sessionId": "abc123",
        }),
        # User message
        json.dumps({
            "type": "user",
            "message": {
                "role": "user",
                "content": "hello",
            },
            "timestamp": "2026-03-28T10:00:00Z",
            "sessionId": "abc123",
        }),
        # Assistant message with usage and thinking
        json.dumps({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_creation_input_tokens": 500,
                    "cache_read_input_tokens": 200,
                },
                "content": [
                    {"type": "thinking", "thinking": "let me think..."},
                    {"type": "text", "text": "Hi there!"},
                ],
            },
            "timestamp": "2026-03-28T10:00:05Z",
            "sessionId": "abc123",
        }),
        # Assistant message with tool_use
        json.dumps({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4",
                "usage": {
                    "input_tokens": 200,
                    "output_tokens": 100,
                },
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_abc",
                        "name": "Read",
                        "input": {"file_path": "/tmp/test.py"},
                    },
                ],
            },
            "timestamp": "2026-03-28T10:00:10Z",
            "sessionId": "abc123",
        }),
        # User message with tool_result
        json.dumps({
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_abc",
                        "content": "file content here",
                    },
                ],
            },
            "timestamp": "2026-03-28T10:00:10Z",
            "sessionId": "abc123",
        }),
        # Final assistant message
        json.dumps({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4",
                "usage": {
                    "input_tokens": 300,
                    "output_tokens": 150,
                },
                "content": [
                    {"type": "text", "text": "Done."},
                ],
            },
            "timestamp": "2026-03-28T10:01:00Z",
            "sessionId": "abc123",
        }),
        # Progress: agent activity (between tool_use and final message)
        json.dumps({
            "type": "progress",
            "data": {
                "type": "agent_progress",
                "agentId": "agent-xyz",
                "message": "working...",
            },
            "timestamp": "2026-03-28T10:00:20Z",
        }),
    ]
    session_file.write_text("\n".join(lines) + "\n")
    return session_file


@pytest.fixture
def mock_subagents(tmp_path):
    """Create mock subagent files."""
    session_dir = tmp_path / ".claude" / "projects" / "test-project" / "abc123"
    sub_dir = session_dir / "subagents"
    sub_dir.mkdir(parents=True)

    agent_file = sub_dir / "agent-xyz.jsonl"
    agent_file.write_text(
        json.dumps({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "sub result"}],
            },
            "timestamp": "2026-03-28T10:00:30Z",
        })
        + "\n"
    )

    meta_file = sub_dir / "agent-xyz.meta.json"
    meta_file.write_text(
        json.dumps({"agentType": "general-purpose", "description": "test agent"})
    )

    return session_dir


class TestParseSession:
    def test_parses_messages(self, mock_session):
        events = parse_session(mock_session)
        messages = [e for e in events if e.get("type") == "message"]
        # user, assistant (thinking), assistant (tool_use), user (tool_result), assistant (done)
        assert len(messages) >= 3

    def test_skips_queue_operations(self, mock_session):
        events = parse_session(mock_session)
        queue_ops = [e for e in events if e.get("type") == "queue-operation"]
        assert len(queue_ops) == 0

    def test_extracts_tokens(self, mock_session):
        events = parse_session(mock_session)
        token_events = [e for e in events if e.get("input_tokens")]
        assert len(token_events) >= 1
        assert token_events[0]["input_tokens"] == 100

    def test_extracts_model(self, mock_session):
        events = parse_session(mock_session)
        model_events = [e for e in events if e.get("model")]
        assert len(model_events) >= 1
        assert model_events[0]["model"] == "claude-sonnet-4"

    def test_extracts_tool_use(self, mock_session):
        events = parse_session(mock_session)
        tools = [e for e in events if e.get("type") == "tool_use"]
        assert len(tools) >= 1
        assert tools[0]["name"] == "Read"
        assert "file" in tools[0]["input_summary"]

    def test_extracts_tool_result(self, mock_session):
        events = parse_session(mock_session)
        results = [e for e in events if e.get("type") == "tool_result"]
        assert len(results) >= 1
        assert results[0]["tool_use_id"] == "toolu_abc"

    def test_detects_thinking(self, mock_session):
        events = parse_session(mock_session)
        thinking = [e for e in events if e.get("has_thinking")]
        assert len(thinking) >= 1

    def test_extracts_agent_progress(self, mock_session):
        events = parse_session(mock_session)
        agents = [e for e in events if e.get("type") == "agent_progress"]
        assert len(agents) >= 1
        assert agents[0]["agent_id"] == "agent-xyz"

    def test_extracts_cache_tokens(self, mock_session):
        events = parse_session(mock_session)
        cache_events = [e for e in events if e.get("cache_creation_tokens")]
        assert len(cache_events) >= 1
        assert cache_events[0]["cache_creation_tokens"] == 500

    def test_handles_empty_file(self, tmp_path):
        f = tmp_path / "empty.jsonl"
        f.write_text("")
        events = parse_session(f)
        assert events == []

    def test_handles_malformed_json(self, tmp_path):
        f = tmp_path / "bad.jsonl"
        f.write_text(
            "not json\n"
            + json.dumps({
                "type": "user",
                "message": {"role": "user", "content": "hi"},
                "timestamp": "2026-03-28T10:00:00Z",
            })
            + "\n"
        )
        events = parse_session(f)
        assert len(events) >= 1

    def test_handles_missing_file(self, tmp_path):
        f = tmp_path / "nonexistent.jsonl"
        events = parse_session(f)
        assert events == []


class TestDiscoverSubagents:
    def test_finds_subagents(self, mock_subagents):
        subs = discover_subagents(mock_subagents)
        assert len(subs) >= 1
        assert subs[0]["agent_id"] == "xyz"

    def test_reads_meta(self, mock_subagents):
        subs = discover_subagents(mock_subagents)
        assert subs[0]["type"] == "general-purpose"
        assert subs[0]["label"] == "test agent"

    def test_counts_messages(self, mock_subagents):
        subs = discover_subagents(mock_subagents)
        assert subs[0]["message_count"] == 1

    def test_empty_dir(self, tmp_path):
        subs = discover_subagents(tmp_path)
        assert subs == []

    def test_no_subagents_dir(self, tmp_path):
        session_dir = tmp_path / "some-session"
        session_dir.mkdir()
        subs = discover_subagents(session_dir)
        assert subs == []

    def test_meta_missing(self, tmp_path):
        sub_dir = tmp_path / "subagents"
        sub_dir.mkdir(parents=True)
        agent_file = sub_dir / "agent-nometafile.jsonl"
        agent_file.write_text(json.dumps({"type": "message"}) + "\n")

        subs = discover_subagents(tmp_path)
        assert len(subs) == 1
        assert subs[0]["agent_id"] == "nometafile"
        assert subs[0]["type"] == ""
        assert subs[0]["label"] == ""


class TestGetSessionMetrics:
    def test_calculates_tokens(self, mock_session):
        metrics = get_session_metrics(mock_session)
        assert metrics["total_input_tokens"] == 600  # 100 + 200 + 300
        assert metrics["total_output_tokens"] == 300  # 50 + 100 + 150

    def test_calculates_cache_tokens(self, mock_session):
        metrics = get_session_metrics(mock_session)
        assert metrics["cache_creation_tokens"] == 500
        assert metrics["cache_read_tokens"] == 200

    def test_counts_tool_uses(self, mock_session):
        metrics = get_session_metrics(mock_session)
        assert metrics["tool_use_count"] >= 1
        tool_names = [t["tool"] for t in metrics["tool_uses"]]
        assert "Read" in tool_names

    def test_detects_model(self, mock_session):
        metrics = get_session_metrics(mock_session)
        assert "claude-sonnet-4" in metrics["models_used"]

    def test_calculates_message_count(self, mock_session):
        metrics = get_session_metrics(mock_session)
        # user + 3 assistant + user (tool_result) = 5 messages
        assert metrics["message_count"] >= 3

    def test_calculates_duration(self, mock_session):
        metrics = get_session_metrics(mock_session)
        assert metrics["duration_minutes"] == 1.0  # 10:00:00 to 10:01:00

    def test_counts_thinking(self, mock_session):
        metrics = get_session_metrics(mock_session)
        assert metrics["thinking_count"] >= 1

    def test_detects_subagents(self, mock_session):
        metrics = get_session_metrics(mock_session)
        # agent-xyz in progress events
        assert metrics["subagent_count"] >= 1

    def test_empty_metrics_on_missing_file(self):
        metrics = get_session_metrics("/tmp/nonexistent-session-parser-test.jsonl")
        assert metrics["total_input_tokens"] == 0
        assert metrics["message_count"] == 0

    def test_has_session_id(self, mock_session):
        metrics = get_session_metrics(mock_session)
        assert metrics["session_id"] == "abc123"


class TestListSessions:
    def test_returns_list(self):
        sessions = list_sessions(project_filter="/nonexistent/path")
        assert isinstance(sessions, list)

    def test_filters_by_project(self, mock_session):
        # list_sessions scans get_sessions_dir(), not tmp_path
        # So this just verifies the API doesn't crash with a filter
        sessions = list_sessions(project_filter="/nonexistent/path/xyz")
        assert isinstance(sessions, list)
        assert len(sessions) == 0


class TestFormatReport:
    def test_format_includes_tokens(self, mock_session):
        metrics = get_session_metrics(mock_session)
        report = format_session_report(metrics)
        assert "token" in report.lower()
        assert "600" in report  # total input tokens

    def test_format_includes_model(self, mock_session):
        metrics = get_session_metrics(mock_session)
        report = format_session_report(metrics)
        assert "claude-sonnet-4" in report

    def test_format_includes_duration(self, mock_session):
        metrics = get_session_metrics(mock_session)
        report = format_session_report(metrics)
        assert "1.0" in report

    def test_format_includes_tool_usage(self, mock_session):
        metrics = get_session_metrics(mock_session)
        report = format_session_report(metrics)
        assert "Read" in report

    def test_format_handles_empty_metrics(self):
        from lib.session_parser import _empty_metrics
        metrics = _empty_metrics()
        report = format_session_report(metrics)
        assert "SESSION METRICS REPORT" in report
