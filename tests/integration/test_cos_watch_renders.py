"""Integration — ADR-034 cos-watch TUI renders from a fed JSONL stream."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import time
from pathlib import Path

import pytest


def _load_watch(project_dir: Path):
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "scripts" / "cos-watch.py"
    assert path.exists(), f"missing {path}"
    os.environ["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    mod_name = "cos_watch_under_test"
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    # Dataclass resolution with `from __future__ import annotations` needs
    # the module to be registered in sys.modules before exec_module.
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fed_jsonl(tmp_path: Path) -> Path:
    feed = tmp_path / "events.jsonl"
    events = [
        {"event_type": "agent_start", "agent_id": "a1",
         "started_at": time.time() - 12.5, "model": "claude-sonnet-4",
         "tool_name": "Agent"},
        {"event_type": "tool_use_start", "agent_id": "a1",
         "tool_name": "Read", "started_at": time.time() - 11.0,
         "tool_input_summary": "handler.go"},
        {"event_type": "progress_marker", "agent_id": "a1",
         "ts": time.time() - 10.0, "step_current": 1, "step_total": 3,
         "message": "scoping"},
        {"event_type": "progress_marker", "agent_id": "a1",
         "ts": time.time() - 5.0, "step_current": 2, "step_total": 3,
         "message": "writing code"},
        {"event_type": "token_usage", "agent_id": "a1",
         "ts": time.time() - 3.0, "input_tokens": 4200,
         "output_tokens": 1800, "cache_read": 1200,
         "model": "claude-sonnet-4"},
    ]
    feed.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return feed


def test_render_snapshot_contains_expected_fields(tmp_path, fed_jsonl,
                                                   capsys):
    module = _load_watch(tmp_path)

    # Ingest manually: exercise the AgentView update path.
    view = module.AgentView(agent_id="a1")
    for line in fed_jsonl.read_text().splitlines():
        view.ingest(json.loads(line))

    panel = module._format_panel(view)
    assert "a1" in panel
    assert "claude-sonnet-4" in panel
    assert "in=4200" in panel
    assert "out=1800" in panel
    assert "cache=1200" in panel
    assert "scoping" in panel
    assert "writing code" in panel
    assert "tools" in panel
    # Elapsed is non-zero because started_at was in the past.
    assert "elapsed" in panel


def test_run_once_with_feed_returns_zero(tmp_path, fed_jsonl, capsys):
    module = _load_watch(tmp_path)
    rc = module.run(agent_id="a1", latest=False, once=True, feed=fed_jsonl)
    assert rc == 0
    captured = capsys.readouterr()
    # Some content must have been written to stdout (either rich panel or
    # plain-text block).
    assert captured.out.strip() or captured.err.strip()


def test_run_once_with_empty_feed_still_renders(tmp_path, capsys):
    module = _load_watch(tmp_path)
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    rc = module.run(agent_id="unknown", latest=False, once=True, feed=empty)
    assert rc == 0


def test_pick_latest_agent(tmp_path):
    module = _load_watch(tmp_path)
    views = {
        "old": module.AgentView(agent_id="old", started_at=100.0),
        "new": module.AgentView(agent_id="new", started_at=500.0),
    }
    assert module._pick_latest_agent(views) == "new"
    assert module._pick_latest_agent({}) is None
