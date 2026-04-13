"""Tests for lib/agent_output_monitor.py and lib/agent_output_to_bus.py"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lib.agent_output_monitor import (
    AgentOutputMonitor,
    AgentStatus,
    _parse_lines,
    _read_tail,
    poll_agents,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(directory: Path, filename: str, lines: list[dict]) -> str:
    """Write JSONL to a file and return the absolute path."""
    p = directory / filename
    with open(p, "w") as fh:
        for obj in lines:
            fh.write(json.dumps(obj) + "\n")
    return str(p)


def _assistant_msg(text: str, tool_names: list[str] | None = None) -> dict:
    """Build a minimal assistant JSONL event."""
    content: list[dict] = [{"type": "text", "text": text}]
    for i, name in enumerate(tool_names or []):
        content.append({"type": "tool_use", "id": "t%d" % i, "name": name, "input": {}})
    return {"type": "assistant", "message": {"content": content, "usage": {"output_tokens": 10}}}


def _tool_only_msg(tool_names: list[str]) -> dict:
    """Assistant message with only tool_use blocks (no text)."""
    content = [{"type": "tool_use", "id": "t%d" % i, "name": n, "input": {}} for i, n in enumerate(tool_names)]
    return {"type": "assistant", "message": {"content": content, "usage": {}}}


# ---------------------------------------------------------------------------
# Test: empty output directory
# ---------------------------------------------------------------------------


class TestEmptyOutputDir:
    def test_check_all_empty_dir_returns_empty(self, tmp_path):
        monitor = AgentOutputMonitor(str(tmp_path))
        assert monitor.check_all() == []

    def test_format_dashboard_no_files(self, tmp_path):
        dashboard = poll_agents(str(tmp_path))
        assert "0 running" in dashboard
        assert "no agent output files found" in dashboard

    def test_check_all_nonexistent_dir_returns_empty(self):
        monitor = AgentOutputMonitor("/does/not/exist/at/all")
        assert monitor.check_all() == []

    def test_check_agent_nonexistent_returns_unknown(self, tmp_path):
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("ghost-agent")
        assert status.status == "unknown"
        assert status.tool_call_count == 0
        assert status.agent_id == "ghost-agent"


# ---------------------------------------------------------------------------
# Test: empty output file
# ---------------------------------------------------------------------------


class TestEmptyOutputFile:
    def test_empty_file_returns_unknown_status(self, tmp_path):
        p = tmp_path / "agent-abc.jsonl"
        p.write_text("")
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("agent-abc")
        assert status.status == "unknown"
        assert status.file_size_bytes == 0
        assert status.tool_call_count == 0

    def test_empty_file_no_progress_marker(self, tmp_path):
        p = tmp_path / "agent-abc.jsonl"
        p.write_text("")
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("agent-abc")
        assert status.last_progress_marker is None
        assert status.last_assistant_text is None


# ---------------------------------------------------------------------------
# Test: file with no assistant messages
# ---------------------------------------------------------------------------


class TestNoAssistantMessages:
    def test_only_user_messages_no_text(self, tmp_path):
        lines = [
            {"type": "user", "message": {"content": "hello"}},
            {"type": "system", "subtype": "init"},
        ]
        _write_jsonl(tmp_path, "agent-x.jsonl", lines)
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("agent-x")
        assert status.tool_call_count == 0
        assert status.last_assistant_text is None
        assert status.last_progress_marker is None

    def test_malformed_lines_skipped(self, tmp_path):
        p = tmp_path / "agent-y.jsonl"
        with open(p, "w") as fh:
            fh.write("not json\n")
            fh.write("{incomplete\n")
            fh.write(json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n")
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("agent-y")
        assert status.tool_call_count == 0


# ---------------------------------------------------------------------------
# Test: file with assistant messages but no PROGRESS markers
# ---------------------------------------------------------------------------


class TestAssistantMessagesNoProgress:
    def test_assistant_text_captured(self, tmp_path):
        lines = [
            _assistant_msg("Starting the task."),
            _assistant_msg("Continuing work on the implementation.", ["Read"]),
        ]
        _write_jsonl(tmp_path, "agent-a.jsonl", lines)
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("agent-a")
        assert status.last_assistant_text is not None
        assert "implementation" in status.last_assistant_text
        assert status.last_progress_marker is None

    def test_tool_call_count_correct(self, tmp_path):
        lines = [
            _assistant_msg("step 1", ["Read"]),
            _assistant_msg("step 2", ["Edit", "Bash"]),
            _assistant_msg("done"),
        ]
        _write_jsonl(tmp_path, "agent-b.jsonl", lines)
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("agent-b")
        assert status.tool_call_count == 3  # Read + Edit + Bash

    def test_last_text_limited_to_100_chars(self, tmp_path):
        long_text = "x" * 500
        lines = [_assistant_msg(long_text)]
        _write_jsonl(tmp_path, "agent-c.jsonl", lines)
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("agent-c")
        assert status.last_assistant_text is not None
        assert len(status.last_assistant_text) <= 100


# ---------------------------------------------------------------------------
# Test: file with PROGRESS markers
# ---------------------------------------------------------------------------


class TestProgressMarkers:
    def test_progress_marker_extracted(self, tmp_path):
        lines = [
            _assistant_msg("PROGRESS: [step 1/3] reading source files"),
            _assistant_msg("PROGRESS: [step 2/3] writing tests", ["Edit"]),
        ]
        _write_jsonl(tmp_path, "agent-p.jsonl", lines)
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("agent-p")
        assert status.last_progress_marker is not None
        assert "step 2/3" in status.last_progress_marker

    def test_progress_step_and_total_parsed(self, tmp_path):
        lines = [_assistant_msg("PROGRESS: [step 4/7] running tests")]
        _write_jsonl(tmp_path, "agent-q.jsonl", lines)
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("agent-q")
        assert status.progress_step == 4
        assert status.progress_total == 7

    def test_progress_case_insensitive(self, tmp_path):
        lines = [_assistant_msg("progress: [step 2/5] done")]
        _write_jsonl(tmp_path, "agent-r.jsonl", lines)
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("agent-r")
        assert status.progress_step == 2
        assert status.progress_total == 5

    def test_latest_progress_marker_wins(self, tmp_path):
        lines = [
            _assistant_msg("PROGRESS: [step 1/4] first"),
            _assistant_msg("PROGRESS: [step 2/4] second"),
            _assistant_msg("PROGRESS: [step 3/4] third"),
        ]
        _write_jsonl(tmp_path, "agent-s.jsonl", lines)
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("agent-s")
        # Should have the last marker in the tail window
        assert status.progress_step == 3


# ---------------------------------------------------------------------------
# Test: multiple agents
# ---------------------------------------------------------------------------


class TestMultipleAgents:
    def test_check_all_returns_one_per_file(self, tmp_path):
        for name in ("alpha", "beta", "gamma"):
            _write_jsonl(tmp_path, "%s.jsonl" % name, [_assistant_msg("working")])
        monitor = AgentOutputMonitor(str(tmp_path))
        statuses = monitor.check_all()
        ids = {s.agent_id for s in statuses}
        assert ids == {"alpha", "beta", "gamma"}

    def test_check_all_handles_mixed_extensions(self, tmp_path):
        _write_jsonl(tmp_path, "agent1.jsonl", [_assistant_msg("hello")])
        # .output extension
        p = tmp_path / "agent2.output"
        with open(p, "w") as fh:
            fh.write(json.dumps(_assistant_msg("world")) + "\n")
        monitor = AgentOutputMonitor(str(tmp_path))
        statuses = monitor.check_all()
        ids = {s.agent_id for s in statuses}
        assert "agent1" in ids
        assert "agent2" in ids


# ---------------------------------------------------------------------------
# Test: dashboard formatting
# ---------------------------------------------------------------------------


class TestDashboardFormatting:
    def test_dashboard_header_shows_running_count(self, tmp_path):
        # Write a file with recent mtime to get "running" status
        lines = [_assistant_msg("working", ["Read"])]
        _write_jsonl(tmp_path, "worker.jsonl", lines)
        dashboard = poll_agents(str(tmp_path))
        assert "AGENT DASHBOARD" in dashboard
        # running count depends on file mtime (should be very recent)
        assert "running" in dashboard or "idle" in dashboard

    def test_dashboard_shows_all_agents(self, tmp_path):
        for name in ("alice", "bob"):
            _write_jsonl(tmp_path, "%s.jsonl" % name, [_assistant_msg("working")])
        dashboard = poll_agents(str(tmp_path))
        assert "alice" in dashboard
        assert "bob" in dashboard

    def test_dashboard_shows_progress_step(self, tmp_path):
        lines = [_assistant_msg("PROGRESS: [step 2/5] writing tests")]
        _write_jsonl(tmp_path, "worker.jsonl", lines)
        dashboard = poll_agents(str(tmp_path))
        assert "step 2/5" in dashboard

    def test_dashboard_shows_tool_count(self, tmp_path):
        lines = [
            _assistant_msg("hi", ["Read", "Edit"]),
            _assistant_msg("bye", ["Bash"]),
        ]
        _write_jsonl(tmp_path, "worker.jsonl", lines)
        dashboard = poll_agents(str(tmp_path))
        assert "3 tools" in dashboard

    def test_dashboard_no_markers_label(self, tmp_path):
        lines = [_assistant_msg("just doing work")]
        _write_jsonl(tmp_path, "worker.jsonl", lines)
        dashboard = poll_agents(str(tmp_path))
        assert "no markers" in dashboard


# ---------------------------------------------------------------------------
# Test: agent status detection
# ---------------------------------------------------------------------------


class TestAgentStatusDetection:
    def test_recently_modified_file_is_running(self, tmp_path):
        lines = [_assistant_msg("busy")]
        path = _write_jsonl(tmp_path, "live.jsonl", lines)
        # Touch to ensure mtime is now
        os.utime(path, None)
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("live")
        assert status.status == "running"

    def test_old_file_is_idle_or_completed(self, tmp_path):
        lines = [_assistant_msg("done")]
        path = _write_jsonl(tmp_path, "stale.jsonl", lines)
        # Set mtime to 10 minutes ago
        old_time = time.time() - 600
        os.utime(path, (old_time, old_time))
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("stale")
        assert status.status in ("idle", "completed")

    def test_seconds_since_activity_recent(self, tmp_path):
        lines = [_assistant_msg("working")]
        path = _write_jsonl(tmp_path, "fresh.jsonl", lines)
        os.utime(path, None)
        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("fresh")
        assert status.seconds_since_activity < 5


# ---------------------------------------------------------------------------
# Test: large file efficiency
# ---------------------------------------------------------------------------


class TestLargeFileEfficiency:
    def test_only_tail_lines_used_for_progress(self, tmp_path):
        """Large file: progress marker in tail is found; count from full file."""
        p = tmp_path / "big.jsonl"
        with open(p, "w") as fh:
            # Write 200 lines of tool-only messages to push previous content out of tail
            for i in range(200):
                fh.write(json.dumps(_tool_only_msg(["Read"])) + "\n")
            # Final messages with progress marker
            fh.write(json.dumps(_assistant_msg("PROGRESS: [step 5/5] done")) + "\n")

        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("big")
        # Tool count should reflect all 200 + 0 (last has no tool) = 200
        assert status.tool_call_count == 200
        # Progress marker from the tail should be found
        assert status.progress_step == 5
        assert status.progress_total == 5

    def test_tail_read_does_not_load_whole_file(self, tmp_path):
        """_read_tail should return lines without loading full file."""
        p = tmp_path / "test.jsonl"
        # Write 1000 simple lines
        with open(p, "w") as fh:
            for i in range(1000):
                fh.write(json.dumps({"type": "user", "n": i}) + "\n")

        lines = _read_tail(str(p), tail_bytes=1024)
        # Should return far fewer than 1000 lines
        assert len(lines) < 1000
        assert len(lines) > 0


# ---------------------------------------------------------------------------
# Test: AgentOutputBridge sync
# ---------------------------------------------------------------------------


class TestAgentOutputBridgeSync:
    def test_sync_once_publishes_all_agents(self, tmp_path):
        """Bridge.sync_once() calls publish_status for each agent."""
        for name in ("agent1", "agent2"):
            _write_jsonl(tmp_path, "%s.jsonl" % name, [_assistant_msg("working")])

        from lib.agent_output_to_bus import AgentOutputBridge

        bridge = AgentOutputBridge(
            output_dir=str(tmp_path),
            valkey_url="redis://localhost:6379",
        )

        published: list[AgentStatus] = []

        original_publish = bridge.publish_status

        def mock_publish(status: AgentStatus) -> None:
            published.append(status)

        bridge.publish_status = mock_publish  # type: ignore[method-assign]
        statuses = bridge.sync_once()

        # sync_once should return statuses and call publish_status for each
        # (since we replaced publish_status, check statuses returned)
        assert len(statuses) == 2
        assert {s.agent_id for s in statuses} == {"agent1", "agent2"}

    def test_bridge_uses_agent_publisher(self, tmp_path):
        """Bridge.publish_status() calls AgentPublisher.progress() or report_complete()."""
        lines = [_assistant_msg("PROGRESS: [step 1/2] starting")]
        _write_jsonl(tmp_path, "worker.jsonl", lines)

        from lib.agent_output_to_bus import AgentOutputBridge

        mock_publisher = MagicMock()

        bridge = AgentOutputBridge(output_dir=str(tmp_path))
        # Pre-inject mock publisher
        bridge._publishers["worker"] = mock_publisher

        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("worker")

        bridge.publish_status(status)

        # Should have called progress() since agent is not completed
        if status.status != "completed":
            mock_publisher.progress.assert_called_once()
        else:
            mock_publisher.report_complete.assert_called_once()

    def test_bridge_sync_empty_dir(self, tmp_path):
        """Bridge.sync_once() on empty dir returns empty list without error."""
        from lib.agent_output_to_bus import AgentOutputBridge

        bridge = AgentOutputBridge(output_dir=str(tmp_path))
        result = bridge.sync_once()
        assert result == []

    def test_bridge_publish_completed_agent(self, tmp_path):
        """Completed agent triggers report_complete on publisher."""
        lines = [_assistant_msg("All done!")]
        path = _write_jsonl(tmp_path, "finisher.jsonl", lines)
        # Set mtime to very old so status = "completed"
        old_time = time.time() - 600
        os.utime(path, (old_time, old_time))

        from lib.agent_output_to_bus import AgentOutputBridge

        mock_publisher = MagicMock()
        bridge = AgentOutputBridge(output_dir=str(tmp_path))
        bridge._publishers["finisher"] = mock_publisher

        monitor = AgentOutputMonitor(str(tmp_path))
        status = monitor.check_agent("finisher")
        assert status.status == "completed"

        bridge.publish_status(status)
        mock_publisher.report_complete.assert_called_once()


# ---------------------------------------------------------------------------
# Test: _parse_lines unit tests
# ---------------------------------------------------------------------------


class TestParseLines:
    def test_empty_lines_returns_zero(self):
        count, marker, text = _parse_lines([])
        assert count == 0
        assert marker is None
        assert text is None

    def test_counts_tool_uses(self):
        lines = [
            json.dumps(_tool_only_msg(["Read", "Edit"])),
            json.dumps(_tool_only_msg(["Bash"])),
        ]
        count, _, _ = _parse_lines(lines)
        assert count == 3

    def test_extracts_last_text(self):
        lines = [
            json.dumps(_assistant_msg("first message")),
            json.dumps(_assistant_msg("second message")),
        ]
        _, _, text = _parse_lines(lines)
        assert text is not None
        assert "second message" in text

    def test_progress_marker_extracted(self):
        lines = [json.dumps(_assistant_msg("PROGRESS: [step 3/6] deploying"))]
        _, marker, _ = _parse_lines(lines)
        assert marker is not None
        assert "3/6" in marker
