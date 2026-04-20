"""Unit tests — ADR-034 AiderStreamingAdapter."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "packages" / "agent-lifecycle" / "lib"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

from harness_adapter.aider_streaming import AiderStreamingAdapter  # noqa: E402
from harness_adapter.base import (  # noqa: E402
    ProgressMarker,
    ToolUseEnd,
    ToolUseStart,
)


def test_parse_live_lines_emits_progress_marker():
    adapter = AiderStreamingAdapter()
    lines = [
        "#### Please refactor the foo module",
        "PROGRESS: [2/5] parsing ast",
    ]
    out = adapter.parse_live_lines(lines, source=Path("/tmp/fake.md"))
    kinds = [type(e) for e in out]
    assert ProgressMarker in kinds
    pm = next(e for e in out if isinstance(e, ProgressMarker))
    assert pm.step_current == 2
    assert pm.step_total == 5
    assert "parsing ast" in pm.message


def test_parse_live_lines_emits_tool_start_and_end():
    adapter = AiderStreamingAdapter()
    lines = [
        "#### user prompt",
        "> Running pytest -x tests/",
        "> Ran shell command: pytest -x tests/",
    ]
    out = adapter.parse_live_lines(lines, source=Path("/tmp/fake2.md"))
    starts = [e for e in out if isinstance(e, ToolUseStart)]
    ends = [e for e in out if isinstance(e, ToolUseEnd)]
    assert len(starts) == 1
    assert len(ends) == 1
    assert starts[0].tool_name == "Running"
    assert ends[0].tool_name == "Ran shell command"


def test_stream_events_tails_growing_file(tmp_path):
    history = tmp_path / ".aider.chat.history.md"
    history.write_text("#### initial\n")
    adapter = AiderStreamingAdapter(project_dir=tmp_path)
    stop = threading.Event()
    collected = []

    def writer():
        time.sleep(0.05)
        with open(history, "a", encoding="utf-8") as fh:
            fh.write("PROGRESS: [1/3] step one\n")
            fh.write("> Running echo hi\n")
            fh.flush()
        time.sleep(0.1)
        stop.set()

    t = threading.Thread(target=writer)
    t.start()
    for ev in adapter.stream_events(history, poll_interval=0.05,
                                    stop_event=stop, max_iterations=30):
        collected.append(ev)
    t.join()

    kinds = [type(e).__name__ for e in collected]
    assert "ProgressMarker" in kinds
    assert "ToolUseStart" in kinds


def test_stream_events_handles_missing_file(tmp_path):
    adapter = AiderStreamingAdapter(project_dir=tmp_path)
    stop = threading.Event()
    stop.set()
    out = list(adapter.stream_events(tmp_path / "does-not-exist.md",
                                     poll_interval=0.01,
                                     stop_event=stop,
                                     max_iterations=1))
    assert out == []


def test_stream_events_byte_offset_is_incremental(tmp_path):
    """Second call must not re-emit events already seen."""
    history = tmp_path / ".aider.chat.history.md"
    history.write_text("#### seed\nPROGRESS: [1/2] a\n")
    adapter = AiderStreamingAdapter(project_dir=tmp_path)
    stop = threading.Event()
    stop.set()
    first_pass = list(adapter.stream_events(history, poll_interval=0.01,
                                            stop_event=stop, max_iterations=1))
    assert any(isinstance(e, ProgressMarker) for e in first_pass)

    # Second call with no file change: no new events
    stop2 = threading.Event()
    stop2.set()
    second_pass = list(adapter.stream_events(history, poll_interval=0.01,
                                             stop_event=stop2,
                                             max_iterations=1))
    assert second_pass == []
